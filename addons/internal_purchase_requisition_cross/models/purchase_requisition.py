# -*- coding: utf-8 -*-
"""
Created on 2025-12-01 15:30:34

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PurchaseRequisitionInherit(models.Model):
    _inherit = 'purchase.requisition'

    def _get_default_allowed_partners(self):
        return self.requested_by.helpdesk_allowed_partner_ids

    products_list = fields.Char(
        string='Detalles de productos', compute='_compute_products_list', store=True)
    product_ids = fields.Many2many(
        'product.product',string="Seleccionar productos", required=True, domain=[('purchase_ok', '=', True)])
    priority_level = fields.Selection(
        string='Prioridad', default='low', tracking=True,
        selection=[
            ('low', 'Baja'),
            ('medium', 'Media'),
            ('high', 'Alta')
    ])
    origin = fields.Char(
        string='Nro. Ficha')
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'In-Review'),
        ('procurement_officer_approved', 'Procurement Officer Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
        ('done','Comprado')
    ], string='Approval Status', default='draft', tracking=True)
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Orden de compra')
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', tracking=True, index=True)
    current_user_allowed_partners = fields.Many2many(
        'res.partner', compute='_compute_current_user_allowed_partners', default=_get_default_allowed_partners, store=False)
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    cancellation_reason = fields.Text(
        string='Motivo de Cancelación', readonly=True, tracking=True)

    @api.depends_context('requested_by')
    def _compute_current_user_allowed_partners(self):
        for record in self:
            if record.requested_by.helpdesk_allowed_partner_ids:
                record.current_user_allowed_partners = record.requested_by.helpdesk_allowed_partner_ids
            
            else:
                record.current_user_allowed_partners = False

    @api.onchange('requested_by')
    def _onchange_requested_by(self):
        if self.requested_by:
            self.current_user_allowed_partners = self.requested_by.helpdesk_allowed_partner_ids
            self.partner_id = False
        else:
            self.current_user_allowed_partners = False
            self.partner_id = False

    @api.depends('requisition_line_ids.product_id') 
    def _compute_products_list(self):
        for record in self:
            names = record.requisition_line_ids.mapped('product_id.name')
            record.products_list = ", ".join(names)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
    
        employee_department = self.env.user.employee_id.department_id if self.env.user.employee_id else False

        if employee_department:
            copy_data = {
                'department_id': employee_department.id,
            }
            res.update(copy_data)
    
        return res

    def create_purchase_order_from_requisition(self):
        """
        Crea Órdenes de Compra agrupando por Proveedor y luego por Producto.
        Si la línea no tiene proveedor, usa el de la compañía.
        """
        # Estructura: { partner_id: { product_key: values } }
        grouped_by_supplier = {}
        requisition_ids_set = set()

        # 1. Validaciones y Agrupación
        for requisition in self:
            if requisition.purchase_order_status not in ['None', 'Cancelled']:
                raise UserError(_("Ya se ha creado una orden para la solicitud '%s'." % requisition.name))
            if requisition.approval_status != 'approved':
                raise UserError(_("La solicitud '%s' no está aprobada." % requisition.name))

            requisition_ids_set.add(requisition.id)

            for line in requisition.requisition_line_ids:
                # Determinamos el proveedor (Línea > Compañía)
                supplier = line.supplier_id or self.env.company.partner_id
                supplier_id = supplier.id

                # Inicializamos el diccionario del proveedor si no existe
                if supplier_id not in grouped_by_supplier:
                    grouped_by_supplier[supplier_id] = {}

                # Clave única de producto
                key = (line.product_id.id, line.product_uom.id, line.product_packaging_id.id)
                line_desc = line.description or line.product_id.name

                # Agrupación dentro del proveedor
                if key in grouped_by_supplier[supplier_id]:
                    # Sumar cantidades
                    grouped_by_supplier[supplier_id][key]['product_qty'] += line.quantity
                    grouped_by_supplier[supplier_id][key]['product_length'] += line.product_length
                    grouped_by_supplier[supplier_id][key]['product_packaging_qty'] += line.product_packaging_qty
                    
                    # Concatenar descripción si es distinta
                    if line_desc and line_desc not in grouped_by_supplier[supplier_id][key]['name']:
                        grouped_by_supplier[supplier_id][key]['name'] += f" | {line_desc}"
                else:
                    # Crear nueva entrada
                    grouped_by_supplier[supplier_id][key] = {
                        'product_id': line.product_id.id,
                        'product_length': line.product_length,
                        'product_qty': line.quantity,
                        'product_uom': line.product_uom.id,
                        'price_unit': line.price,
                        'name': line_desc,
                        'product_packaging_id': line.product_packaging_id.id,
                        'product_packaging_qty': line.product_packaging_qty,
                        'date_planned': fields.Datetime.now(),
                    }

        if not grouped_by_supplier:
            raise UserError(_("No hay líneas disponibles para crear pedidos."))

        # 2. Creación de las Órdenes de Compra
        new_po_ids = []
        
        # Iteramos por cada proveedor encontrado
        for partner_id, products in grouped_by_supplier.items():
            # Convertimos los productos agrupados a comandos
            order_lines_commands = [Command.create(vals) for vals in products.values()]

            po_vals = {
                'partner_id': partner_id,
                'origin': ', '.join(self.mapped('name')),
                'requisition_ids': [Command.set(list(requisition_ids_set))],
                'order_line': order_lines_commands,
                'company_id': self[0].company_id.id,
                'state': 'draft',
            }
            po = self.env['purchase.order'].create(po_vals)
            new_po_ids.append(po.id)

        # 3. Actualizar estados
        self._compute_purchase_order_status()

        # 4. Retorno Dinámico (Formulario o Lista)
        return self._get_dynamic_po_action(new_po_ids)

    def purchase_requisition_select_product(self):
        self.ensure_one()
        return {
            'name': _('Seleccionar múltiples productos'),
            'type': 'ir.actions.act_window',
            'res_model': 'mp.purchase.requisition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_department_id': self.department_id.id,
                'active_id': self.id,
                'active_model': 'purchase.requisition'
            }
        }

    def approve_in_one_step(self):
        """Aprueba la requisición en un sólo paso"""
        self.ensure_one()
        self.action_submit()
        self.action_approve_by_procurement_officer()
        self.action_approve_by_manager()

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'inline',
        }

    def action_create_purchase_order(self):
        """
        Crea POs desde la requisición.
        - CASO A (Rápida): Si hay líneas marcadas, crea UNA sola compra.
        - CASO B (Estándar): Si no hay marcadas, separa por proveedor.
        - LOGICA ESTADO: Solo pasa a 'done' si no quedan líneas pendientes.
        """
        # 1. Obtener líneas disponibles (que no tienen compra aún)
        available_lines = self.requisition_line_ids.filtered(lambda l: not l.purchase_order_line_id)

        if not available_lines:
             raise UserError(_('Todas las líneas de esta requisición ya han sido procesadas.'))

        # 2. Verificar si hay selección manual ("Compra Rápida")
        quick_lines = available_lines.filtered(lambda l: l.create_quick_purchase)
        
        lines_grouped_by_partner = {}

        if quick_lines:
            # === CASO A: COMPRA RÁPIDA ===
            company_partner_id = self.env.company.partner_id.id
            lines_grouped_by_partner[company_partner_id] = quick_lines
        else:
            # === CASO B: PROCESO ESTÁNDAR ===
            for line in available_lines:
                supplier_id = (line.supplier_id or self.env.company.partner_id).id
                if supplier_id not in lines_grouped_by_partner:
                    lines_grouped_by_partner[supplier_id] = self.env['purchase.requisition.line']
                lines_grouped_by_partner[supplier_id] |= line

        # 3. Creación de Órdenes de Compra
        new_po_ids = []

        for partner_id, lines in lines_grouped_by_partner.items():
            po_lines_commands = []
            lines_to_link = [] 

            for line in lines:
                cmd = Command.create({
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'price_unit': line.price,
                    'name': line.description or line.product_id.name,
                    'product_uom': line.product_uom.id,
                    'date_planned': fields.Datetime.now(),
                    'product_packaging_id': line.product_packaging_id.id,
                    'product_packaging_qty': line.product_packaging_qty,
                    'product_length': line.product_length,
                })
                po_lines_commands.append(cmd)
                lines_to_link.append(line)

            po_vals = {
                'partner_id': partner_id,
                'origin': self.name,
                'requisition_ids': [Command.link(self.id)],
                'order_line': po_lines_commands,
                'company_id': self.company_id.id,
                'state': 'draft',
            }
            
            po = self.env['purchase.order'].create(po_vals)
            new_po_ids.append(po.id)

            # 4. VINCULACIÓN: Requisición <-> Compra
            created_po_lines = po.order_line
            
            if len(lines_to_link) == len(created_po_lines):
                for req_line, po_line in zip(lines_to_link, created_po_lines):
                    req_line.write({
                        'purchase_order_line_id': po_line.id,
                        'create_quick_purchase': False
                    })

        # Buscamos si queda alguna línea que NO tenga compra y que NO esté rechazada.
        pending_lines = self.requisition_line_ids.filtered(
            lambda l: not l.purchase_order_line_id and not l.refused
        )

        if not pending_lines:
            # Si no queda nada pendiente, cerramos la requisición
            self.write({'approval_status': 'done'})
        else:
            # Si quedan cosas, aseguramos que siga en estado aprobado para seguir comprando
            self.write({'approval_status': 'approved'})

        # 5. Actualizar referencia en cabecera
        if new_po_ids:
            self.purchase_order_id = new_po_ids[0]

        # 6. Retorno Dinámico
        context = {}
        if quick_lines:
            context['form_view_initial_mode'] = 'edit'

        return self._get_dynamic_po_action(new_po_ids, context)

    def _get_dynamic_po_action(self, new_po_ids, extra_context=None):
        """
        Retorna la acción correcta dependiendo de cuántas compras se crearon.
        """
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'target': 'current',
            'context': extra_context or {}
        }

        if len(new_po_ids) == 1:
            # Caso A: Una sola compra -> Abrir formulario
            action.update({
                'name': _('Orden de Compra Creada'),
                'view_mode': 'form',
                'res_id': new_po_ids[0],
            })
        else:
            # Caso B: Múltiples compras -> Abrir lista filtrada
            action.update({
                'name': _('Órdenes de Compra Generadas'),
                'view_mode': 'list,form',
                'domain': [('id', 'in', new_po_ids)],
            })
        
        return action

    def action_cancel(self):
        """
        Abre el wizard para ingresar el motivo de cancelación.
        """
        self.ensure_one()
        return {
            'name': 'Cancelar Requisición',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_requisition_id': self.id,
                'default_reason': self.cancellation_reason or ''
            }
        }

    def reset_draft(self):
        # 1. Limpiamos el vínculo con la línea de compra en TODAS las líneas de la requisición
        self.mapped('requisition_line_ids').write({
            'purchase_order_line_id': False,
            'create_quick_purchase': False
        })

        # 2. Limpiar también el campo de la cabecera si lo usas
        self.purchase_order_id = False 

        # 3. Cambiamos el estado a borrador
        self.write({'approval_status': 'draft'})


class PurchaseRequisitionLineInherit(models.Model):
    _inherit = 'purchase.requisition.line'

    product_id = fields.Many2one(
        'product.product', string="Producto", required=True, tracking=True,
        domain="[('purchase_ok', '=', True), ('id', 'in', allowed_department_product_ids)]")
    allowed_department_product_ids = fields.Many2many(
        related='requisition_id.department_id.department_product_ids', readonly=True, string="Productos Permitidos por Depto")
    apply_weight_product = fields.Boolean(
        related='product_id.apply_weight_product')
    product_length = fields.Float(
        string='Largo (Mts.)', digits='Product Unit of Measure')
    company_id = fields.Many2one(
        related='requisition_id.company_id', string='Compañía', store=True, readonly=True)
    product_packaging_id = fields.Many2one(
        'product.packaging', string='Embalaje', domain="[('purchase', '=', True), ('product_id', '=', product_id)]", check_company=True,
        compute="_compute_product_packaging_id", store=True, readonly=False)
    product_packaging_qty = fields.Float(
        'Cantidad de embalaje', compute="_compute_product_packaging_qty", store=True, readonly=False)
    product_packaging_linear_meter = fields.Float(
        related='product_packaging_id.linear_meter')
    product_packaging_linear_meter_total = fields.Float(
        string='Total metro lineal', compute='_compute_product_packaging_linear_meter_total')
    supplier_id = fields.Many2one(
        'res.partner', string='Proveedor')
    refused = fields.Boolean(
        string='Rechazado?')
    refused_reason = fields.Char(
        string='Motivo del rechazo')
    create_quick_purchase = fields.Boolean(
        string='Crear compra rápida')
    purchase_order_id = fields.Many2one(
        'purchase.order', related='purchase_order_line_id.order_id', string='Orden de compra', store=False, readonly=True)
    purchase_order_line_id = fields.Many2one(
        'purchase.order.line', string='Línea de la orden de compra')
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            self.supplier_id = False
            return

        # 1. Buscar la última compra confirmada (purchase) o bloqueada (done)
        last_po_line = self.env['purchase.order.line'].search(
            [
                ('product_id', '=', self.product_id.id),
                ('state', 'in', ['purchase', 'done']),
                ('company_id', '=', self.env.company.id)
            ],
            order='order_id desc',
            limit=1
        )

        if last_po_line:
            # Obtenemos el proveedor de la orden padre
            self.supplier_id = last_po_line.order_id.partner_id
        
        elif self.product_id.seller_ids:
            # 2. Si no hay compras previas, usamos el Proveedor Principal (el primero de la lista)
            self.supplier_id = self.product_id.seller_ids[0].partner_id
        
        else:
            self.supplier_id = False
       
    @api.depends('product_packaging_linear_meter', 'product_packaging_qty')
    def _compute_product_packaging_linear_meter_total(self):
        for record in self:
            record.product_packaging_linear_meter_total = record.product_packaging_linear_meter * record.product_packaging_qty
    
    @api.depends('product_id', 'quantity', 'product_uom', 'product_length', 'company_id')
    def _compute_product_packaging_id(self):
        for line in self:
            product_qty = line.quantity if not line.apply_weight_product else line.product_length
            
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            
            if line.product_id and product_qty and line.product_uom:
                suggested_packaging = line.product_id.packaging_ids\
                        .filtered(lambda p: p.purchase and (p.product_id.company_id <= p.company_id <= line.company_id))\
                        ._find_suitable_product_packaging(product_qty, line.product_uom)
                
                line.product_packaging_id = suggested_packaging or line.product_packaging_id

    @api.depends('product_packaging_id', 'product_uom', 'quantity', 'product_length')
    def _compute_product_packaging_qty(self):
        for line in self:
            if not line.product_packaging_id:
                line.product_packaging_qty = 0

            else:
                product_qty = line.quantity if not line.apply_weight_product else line.product_length                
                packaging_uom = line.product_packaging_id.product_uom_id

                if packaging_uom == line.product_uom:
                    line.product_packaging_qty = product_qty / line.product_packaging_id.qty

                else:
                    line.product_packaging_qty = product_qty / line.product_packaging_id._check_qty(1, packaging_uom, 'UP')

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        if self.product_packaging_id and self.quantity:
            newqty = self.product_packaging_id._check_qty(self.quantity, self.product_uom, "UP")
            if float_compare(newqty, self.quantity, precision_rounding=self.product_uom.rounding) != 0:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            "This product is packaged by %(pack_size).2f %(pack_name)s. You should purchase %(quantity).2f %(unit)s.",
                            pack_size=self.product_packaging_id.qty,
                            pack_name=self.product_id.uom_id.name,
                            quantity=newqty,
                            unit=self.product_uom.name
                        ),
                    },
                }

    @api.onchange('product_packaging_qty')
    def _onchange_product_packaging_qty(self):
        """
        Calcula la cantidad total (Quantity o Length) cuando el usuario 
        modifica manualmente la cantidad de paquetes/bultos.
        """
        if not self.product_packaging_id:
            return

        total_qty = self.product_packaging_id.qty * self.product_packaging_qty

        if self.product_packaging_id.product_uom_id != self.product_uom:
            total_qty = self.product_packaging_id.product_uom_id._compute_quantity(
                total_qty, self.product_uom)

        if self.apply_weight_product:
            self.product_length = total_qty

        else:
            self.quantity = total_qty

    def unlink(self):
        """
        Bloqueamos el borrado si la requisición no está en borrador o enviada.
        """
        for line in self:
            # Verificamos el estado del padre
            if line.requisition_id.approval_status not in ['draft', 'submitted']:
                raise UserError(_("No puedes eliminar líneas cuando la requisición está en proceso de aprobación o finalizada."))
        
        return super().unlink()
