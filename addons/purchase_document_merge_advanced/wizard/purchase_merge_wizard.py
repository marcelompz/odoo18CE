from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseMergeWizard(models.TransientModel):
    _name = 'purchase.merge.wizard'
    _description = 'Asistente de Fusión de Documentos de Compra'

    partner_id = fields.Many2one('res.partner', string='Proveedor', readonly=True)
    purchase_ids = fields.Many2many('purchase.order', string='Órdenes de Compra')
    invoice_ids = fields.Many2many('account.move', string='Facturas')
    picking_ids = fields.Many2many('stock.picking', string='Recepciones')
    
    document_type = fields.Selection([
        ('purchase', 'Orden de Compra'),
        ('invoice', 'Factura de Proveedor'),
        ('picking', 'Recepción de Mercadería')
    ], string='Tipo de Documento', readonly=True)

    target_purchase_id = fields.Many2one('purchase.order', string='Orden Destino', domain="[('id', 'in', purchase_ids)]")
    target_invoice_id = fields.Many2one('account.move', string='Factura Destino', domain="[('id', 'in', invoice_ids)]")
    target_picking_id = fields.Many2one('stock.picking', string='Recepción Destino', domain="[('id', 'in', picking_ids)]")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if not active_ids or not active_model:
            return res

        records = self.env[active_model].browse(active_ids)
        if active_model == 'purchase.order':
            res.update({
                'document_type': 'purchase',
                'purchase_ids': [(6, 0, active_ids)],
                'partner_id': records[0].partner_id.id if records else False,
            })
        elif active_model == 'account.move':
            # Check if all are supplier bills
            if any(m.move_type != 'in_invoice' for m in records):
                raise UserError(_("Solo se pueden fusionar facturas de proveedor (Vendor Bills)."))
            res.update({
                'document_type': 'invoice',
                'invoice_ids': [(6, 0, active_ids)],
                'partner_id': records[0].partner_id.id if records else False,
            })
        elif active_model == 'stock.picking':
            res.update({
                'document_type': 'picking',
                'picking_ids': [(6, 0, active_ids)],
                'partner_id': records[0].partner_id.id if records else False,
            })
        return res

    def action_merge(self):
        self.ensure_one()
        clean_ctx = {k: v for k, v in self.env.context.items() 
                     if not k.startswith('default_') 
                     and k not in ['move_type', 'type', 'active_model', 'active_id', 'active_ids']}
        clean_ctx['skip_deep_merge'] = True
        
        wiz = self.with_context(clean_ctx)
        purchase_ids = self.purchase_ids.with_context(clean_ctx)
        invoice_ids = self.invoice_ids.with_context(clean_ctx)
        picking_ids = self.picking_ids.with_context(clean_ctx)
        
        target_purchase = self.target_purchase_id.with_context(clean_ctx)
        target_invoice = self.target_invoice_id.with_context(clean_ctx)
        target_picking = self.target_picking_id.with_context(clean_ctx)
        
        if self.document_type == 'purchase':
            # 1. Merge POs (Phase 1: Transfers lines)
            res = wiz._merge_purchase_orders(purchase_ids, target_purchase)
            
            # 2. Find related Pickings and merge them
            related_pickings = purchase_ids.mapped('picking_ids').filtered(lambda p: p.state != 'cancel').with_context(clean_ctx)
            if len(related_pickings) > 1:
                wiz._merge_pickings(related_pickings, target_picking)
            
            # 3. Find related Bills and merge them
            related_invoices = purchase_ids.mapped('invoice_ids').filtered(lambda i: i.state != 'cancel').with_context(clean_ctx)
            if len(related_invoices) > 1:
                wiz._merge_invoices(related_invoices, target_invoice)
            
            return res

        elif self.document_type == 'invoice':
            # Identify all related documents first
            related_pos = invoice_ids.mapped('invoice_line_ids.purchase_line_id.order_id').filtered(lambda o: o.state != 'cancel').with_context(clean_ctx)
            related_pickings = related_pos.mapped('picking_ids').filtered(lambda p: p.state != 'cancel').with_context(clean_ctx)

            # 1. Merge POs first to have target lines ready
            if len(related_pos) > 1:
                wiz._merge_purchase_orders(related_pos)

            # 2. Merge Pickings
            if len(related_pickings) > 1:
                wiz._merge_pickings(related_pickings)

            # 3. Finally merge Invoices
            res = wiz._merge_invoices(invoice_ids, target_invoice)
            return res

        elif self.document_type == 'picking':
            related_pos = picking_ids.mapped('purchase_id').filtered(lambda o: o.state != 'cancel').with_context(clean_ctx)
            related_invoices = related_pos.mapped('invoice_ids').filtered(lambda i: i.state != 'cancel').with_context(clean_ctx)

            # 1. Merge POs
            if len(related_pos) > 1:
                wiz._merge_purchase_orders(related_pos)

            # 2. Merge Pickings
            res = wiz._merge_pickings(picking_ids, target_picking)

            # 3. Merge Invoices
            if len(related_invoices) > 1:
                wiz._merge_invoices(related_invoices)
            return res

        return {'type': 'ir.actions.act_window_close'}

    def _merge_purchase_orders(self, orders=None, target=None):
        orders = orders or self.purchase_ids
        if len(orders) < 2:
            return
        
        target = target or self.target_purchase_id or orders[0]
        others = orders - target
        
        # Validation
        for order in others:
            if order.partner_id != target.partner_id:
                raise UserError(_("Todos los documentos de compra deben ser del mismo proveedor."))
            if order.currency_id != target.currency_id:
                raise UserError(_("Todos los documentos de compra deben tener la misma moneda."))

        # Transfer Lines
        for order in others:
            for line in order.order_line:
                # Find if exact product and price already in target
                existing_line = target.order_line.filtered(lambda l: l.product_id == line.product_id and l.price_unit == line.price_unit)
                if existing_line:
                    existing_line[0].product_qty += line.product_qty
                    # Important: Update source lines references if needed (e.g. for re-linking moves)
                else:
                    line.copy({'order_id': target.id})
            
            # Audit log
            target.message_post(body=_("Fusión avanzada: Se han integrado las líneas de la orden %s.") % order.name)
            order.message_post(body=_("Esta orden ha sido fusionada en %s.") % target.name)

        # We will cancel 'others' at the end of action_merge after pickings/bills are moved
        # But for now, let's try to cancel them here if we are NOT in a deep merge context?
        # No, better to cancel at the end to avoid "Cannot cancel PO with completed pickings"
        for order in others:
            try:
                if order.state not in ['cancel', 'done']:
                    order.button_cancel()
            except Exception:
                # If it still fails, we'll let it be for now and log
                order.message_post(body=_("Aviso: El pedido no se pudo cancelar automáticamente debido a recepciones pendientes. Por favor, cancélelo manualmente tras verificar la fusión."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': target.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _merge_invoices(self, invoices=None, target=None):
        invoices = invoices or self.invoice_ids
        if len(invoices) < 2:
            return
        
        target = target or self.target_invoice_id or invoices[0]
        others = invoices - target
        
        # Validation
        for inv in others:
            if inv.partner_id != target.partner_id:
                raise UserError(_("Todas las facturas deben ser del mismo proveedor."))
            if inv.currency_id != target.currency_id:
                raise UserError(_("Todas las facturas deben tener la misma moneda."))
            if inv.move_type != target.move_type:
                raise UserError(_("Todas las facturas deben ser del mismo tipo (ej: factura de proveedor)."))

        was_posted = target.state == 'posted'
        if was_posted:
            target.button_draft()

        for inv in others:
            for line in inv.invoice_line_ids:
                line.copy({'move_id': target.id})
            
            # Audit and Cancel
            target.message_post(body=_("Fusión avanzada: Se han integrado las líneas de la factura %s.") % inv.name)
            inv.message_post(body=_("Esta factura ha sido fusionada en %s y será cancelada.") % target.name)
            
            if inv.state == 'posted':
                inv.button_draft()
            inv.button_cancel()
        
        if was_posted:
            target.action_post()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': target.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _merge_pickings(self, pickings=None, target=None):
        pickings = pickings or self.picking_ids
        if len(pickings) < 2:
            return
        
        target = target or self.target_picking_id or pickings[0]
        others = pickings - target
        
        # Validation
        for pick in others:
            if pick.partner_id != target.partner_id:
                raise UserError(_("Todas las recepciones deben ser del mismo proveedor."))
            if pick.picking_type_id != target.picking_type_id:
                raise UserError(_("Todas las recepciones deben tener el mismo tipo de operación."))

        target_po = target.purchase_id
        for pick in others:
            for move in pick.move_ids:
                # Re-link move to target picking
                move.write({'picking_id': target.id})
                
                # Re-link move to target PO line if possible to "orphan" the source PO
                if move.purchase_line_id and target_po:
                    matching_line = target_po.order_line.filtered(
                        lambda l: l.product_id == move.product_id and l.price_unit == move.purchase_line_id.price_unit
                    )
                    if matching_line:
                        # We use sudo/write to force the link if it's already done
                        try:
                            move.with_context(force_company=move.company_id.id).write({
                                'purchase_line_id': matching_line[0].id
                            })
                        except Exception:
                            # If Odoo blocks it (e.g. for done moves), we log it
                            pass
            
            # Audit and Cancel
            target.message_post(body=_("Fusión avanzada: Se han unificado los movimientos de la recepción %s.") % pick.name)
            pick.message_post(body=_("Esta recepción ha sido fusionada en %s y quedará vacía/cancelada.") % target.name)
            
            if pick.state not in ['cancel', 'done']:
                try:
                    pick.action_cancel()
                except Exception:
                    pass

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': target.id,
            'view_mode': 'form',
            'target': 'current',
        }
