from odoo import models, fields, api

class MassiveCostUpdateWizard(models.TransientModel):
    _name = 'massive.cost.update.wizard'
    _description = 'Massive Cost Update Wizard'

    new_cost = fields.Float(string='New Cost', required=True)

    def action_update_cost(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}
        
        product_variants = self.env['product.product'].browse(active_ids)
        product_variants.write({'standard_price': self.new_cost})
        
        return {'type': 'ir.actions.act_window_close'}
