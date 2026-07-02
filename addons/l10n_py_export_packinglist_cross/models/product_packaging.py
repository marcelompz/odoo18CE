# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    package_empty_weight = fields.Float(
        string='Peso Empaque Vacio (kg)',
        digits=(16, 3),
        help='Peso del empaque sin contenido (kg). Se usa para calcular el peso bruto '
             'del Packing List = peso neto de productos + (numero de bultos * este peso). '
             'Si lo dejas en 0, se intentara leer del Tipo de Empaque (stock.package.type) '
             'asociado, si lo hay.',
    )
