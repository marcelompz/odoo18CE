from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    code = fields.Char(string='Código', help='Código de la categoría de producto')

