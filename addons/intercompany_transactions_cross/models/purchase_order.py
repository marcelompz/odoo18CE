# intercompany_transactions_cross/models/purchase_order.py
from odoo import models, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_create_sale_order_wizard(self):
        self.ensure_one()
        view = self.env.ref('intercompany_transactions_cross.create_sale_order_wizard_view_form')
        
        # Prepare lines to pass via default_line_ids context
        line_values = []
        for line in self.order_line:
            if line.product_id:
                line_values.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': line.product_qty,
                    'uom_id': line.product_uom.id,
                    'purchase_price': line.price_unit,
                    'sale_price': line.price_unit,
                }))

        return {
            'name': 'Crear Venta con Margen',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'create.sale.order.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_line_ids': line_values,
                'default_company_id': self.company_id.id,
                'default_currency_id': self.currency_id.id,
            }
        }
