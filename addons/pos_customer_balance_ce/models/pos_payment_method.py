from odoo import models, fields, api

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pricelist_id = fields.Many2one('product.pricelist', string='Associated Pricelist', help='If set, this pricelist will be automatically applied to the entire order when this payment method is selected.')

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        return result + ['pricelist_id']
