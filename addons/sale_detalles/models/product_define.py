from odoo import models, fields, api

class ProductDefine(models.Model):
    _name = 'product.define'
    _description = 'Definición de Productos con Variantes'

    name = fields.Char(string='Nombre', required=True)
    product1_id = fields.Many2one('product.template', string='Producto 1', required=True)
    product2_id = fields.Many2one('product.template', string='Producto 2')
    product3_id = fields.Many2one('product.template', string='Producto 3')
    product4_id = fields.Many2one('product.template', string='Producto 4')
    product5_id = fields.Many2one('product.template', string='Producto 5') 