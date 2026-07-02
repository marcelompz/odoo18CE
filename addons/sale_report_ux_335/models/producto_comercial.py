# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductoComercial(models.Model):
    _name = 'producto.comercial'
    _description = 'Producto Comercial'
    _order = 'sequence, name'

    name = fields.Char('Nombre', required=True)
    descripcion = fields.Text('Descripción')
    list_price = fields.Float('Precio', digits='Product Price', required=True, default=0.0)
    sequence = fields.Integer('Secuencia', default=10)
    active = fields.Boolean('Activo', default=True)
