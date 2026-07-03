from odoo import fields, models

class LotValidationLog(models.Model):
    _name = 'lot.validation.log'
    _description = 'Lot Validation Log'
    _order = 'date desc'

    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    date = fields.Datetime(string='Date Processed', default=fields.Datetime.now)
    state = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial/Negative'),
        ('failed', 'Failed')
    ], string='Result Status')
    notes = fields.Text(string='Details')
