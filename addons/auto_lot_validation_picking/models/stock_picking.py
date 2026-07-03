from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    lot_validation_state = fields.Selection([
        ('pending', 'Pending Allocation'),
        ('partial', 'Partially Validated (Neg)'),
        ('negative', 'With Negative Inventory'),
        ('done', 'Completed')
    ], string='Lot Validation State', compute='_compute_lot_validation_state', store=True)

    has_negative_records = fields.Boolean(compute='_compute_has_negative_records')

    @api.depends('state', 'move_line_ids.quantity', 'move_line_ids.lot_id')
    def _compute_lot_validation_state(self):
        for picking in self:
            if picking.state == 'done':
                negative_recs = self.env['stock.negative.record'].search_count([('picking_id', '=', picking.id)])
                if negative_recs > 0:
                    picking.lot_validation_state = 'negative'
                else:
                    picking.lot_validation_state = 'done'
            elif picking.state == 'assigned':
                picking.lot_validation_state = 'pending'
            else:
                picking.lot_validation_state = False

    def _compute_has_negative_records(self):
        for picking in self:
            count = self.env['stock.negative.record'].search_count([('picking_id', '=', picking.id)])
            picking.has_negative_records = bool(count)

    def action_view_negative_records(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('auto_lot_validation_picking.action_stock_negative_record')
        action['domain'] = [('picking_id', '=', self.id)]
        return action

    def action_auto_assign_lots_and_validate(self):
        for picking in self.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing'):
            log_notes = ""
            has_negative = False
            
            # Standard constraints in Odoo might block validations for tracked products if missing lot, 
            # so we create a dummy NEGATIVE lot if we must bypass it.
            
            for move in picking.move_ids.filtered(lambda m: m.product_id.tracking in ['lot', 'serial']):
                location = move.location_id
                product = move.product_id
                
                # Reset quantity on lines without a lot to ensure we allocate properly
                for ml in move.move_line_ids.filtered(lambda l: not l.lot_id and l.quantity > 0):
                    ml.quantity = 0
                
                qty_to_assign = move.product_uom_qty - sum(move.move_line_ids.mapped('quantity'))
                
                # Clean up any empty move lines without lot_id upfront
                unused_mls = move.move_line_ids.filtered(lambda ml: ml.quantity == 0 and not ml.lot_id)
                if unused_mls:
                    unused_mls.unlink()

                if qty_to_assign <= 0:
                    continue
                
                # Fetch available lots by FIFO
                quants = self.env['stock.quant'].search([
                    ('location_id', 'child_of', location.id),
                    ('product_id', '=', product.id),
                    ('lot_id', '!=', False),
                    ('quantity', '>', 0)
                ], order='in_date asc, id asc')

                available_lots = []
                for quant in quants:
                    avail_qty = quant.quantity - quant.reserved_quantity
                    if avail_qty > 0:
                        available_lots.append({
                            'lot_id': quant.lot_id,
                            'qty': avail_qty,
                            'location_id': quant.location_id,
                        })

                for avail in available_lots:
                    if qty_to_assign <= 0:
                        break
                    take_qty = 1 if product.tracking == 'serial' else min(avail['qty'], qty_to_assign)
                    
                    empty_ml = move.move_line_ids.filtered(lambda ml: not ml.lot_id and ml.quantity == 0)
                    if empty_ml:
                        empty_ml[0].write({
                            'lot_id': avail['lot_id'].id,
                            'quantity': take_qty,
                            'location_id': avail['location_id'].id,
                        })
                    else:
                        self.env['stock.move.line'].create({
                            'move_id': move.id,
                            'product_id': product.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': avail['location_id'].id,
                            'location_dest_id': move.location_dest_id.id,
                            'lot_id': avail['lot_id'].id,
                            'quantity': take_qty,
                            'picking_id': picking.id,
                        })
                    qty_to_assign -= take_qty
                    avail['qty'] -= take_qty

                if qty_to_assign > 0:
                    has_negative = True
                    log_notes += f"Missing {qty_to_assign} {move.product_uom.name} of {product.display_name} (Negative allowed).\n"
                    
                    self.env['stock.negative.record'].create({
                        'product_id': product.id,
                        'picking_id': picking.id,
                        'quantity': qty_to_assign,
                        'location_id': location.id,
                    })

                    # Setup negative lot to avoid core blocker
                    dummy_lot = self.env['stock.lot'].search([
                        ('product_id', '=', product.id),
                        ('name', '=', 'NEGATIVE_ADJ')
                    ], limit=1)
                    if not dummy_lot:
                        dummy_lot = self.env['stock.lot'].create({
                            'name': 'NEGATIVE_ADJ',
                            'product_id': product.id,
                            'company_id': picking.company_id.id,
                        })
                        
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': product.id,
                        'product_uom_id': move.product_uom.id,
                        'location_id': location.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': dummy_lot.id,
                        'quantity': qty_to_assign,
                        'picking_id': picking.id,
                    })
                    
                    picking.activity_schedule(
                        'mail.mail_activity_data_warning',
                        summary=_('Negative Inventory Generated'),
                        note=_('Validated with missing quantity (auto-filled with NEGATIVE_ADJ lot) for product %s', product.display_name),
                        user_id=self.env.user.id
                    )

                # Clean up any remaining empty move lines without lot_id to prevent validation errors
                unused_mls = move.move_line_ids.filtered(lambda ml: ml.quantity == 0 and not ml.lot_id)
                if unused_mls:
                    unused_mls.unlink()

            # Untracked products
            for move in picking.move_ids.filtered(lambda m: m.product_id.tracking == 'none'):
                qty_to_assign = move.product_uom_qty - sum(move.move_line_ids.mapped('quantity'))
                if qty_to_assign > 0:
                    empty_ml = move.move_line_ids.filtered(lambda ml: ml.quantity == 0)
                    if empty_ml:
                        empty_ml[0].quantity = qty_to_assign
                    else:
                        self.env['stock.move.line'].create({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'quantity': qty_to_assign,
                            'picking_id': picking.id,
                        })
                        
                    # Still consider if it's missing from actual stock inside internal locations? 
                    # For untracked products, standard Odoo allows going into negative automatically without blocking 
                    # as long as qty done is set.
                    # We could also log negative record for untracked items if we want. Let's do it.
                    available_qty = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id)
                    if available_qty < qty_to_assign:
                        missing = qty_to_assign - available_qty
                        has_negative = True
                        log_notes += f"Missing {missing} {move.product_uom.name} of untracked product {move.product_id.display_name}.\n"
                        self.env['stock.negative.record'].create({
                            'product_id': move.product_id.id,
                            'picking_id': picking.id,
                            'quantity': missing,
                            'location_id': move.location_id.id,
                        })

            try:
                # Bypass immediate transfer if possible, or directly validate. 
                picking.with_context(skip_sms=True, skip_backorder=True, button_validate_picking_ids=picking.ids).button_validate()
            except Exception as e:
                log_notes += f"Validation error: {str(e)}\n"
            
            state = 'failed' if 'Validation error' in log_notes else ('partial' if has_negative else 'success')
            self.env['lot.validation.log'].create({
                'picking_id': picking.id,
                'state': state,
                'notes': log_notes or "Successfully allocated and validated."
            })
