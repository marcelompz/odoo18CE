from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'
 
    sequence = fields.Integer(string='Secuencia', default=10)
    default_product_id = fields.Many2one('product.product', string='Producto Principal de Fabricación',
        help='Producto que se utilizará como base para la fabricación en esta categoría')
    production_product_id = fields.Many2one('product.product', string='Producto General de Producción',
        help='Producto que se utilizará para registrar el trabajo en esta categoría')

