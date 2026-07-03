from odoo import api, fields, models

class StockNegativeRecord(models.Model):
    _name = 'stock.negative.record'
    _description = 'Negative Stock Adjustment Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, readonly=True)
    quantity = fields.Float(string='Missing Quantity', required=True, readonly=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True, readonly=True)
    state = fields.Selection([
        ('pending', 'Pending Adjustment'),
        ('reconciled', 'Reconciled')
    ], string='Status', default='pending', tracking=True)
    location_id = fields.Many2one('stock.location', string='Missing from Location')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.negative.record') or 'New'
        return super().create(vals_list)
        
    def action_reconcile(self):
        for record in self:
            record.state = 'reconciled'
