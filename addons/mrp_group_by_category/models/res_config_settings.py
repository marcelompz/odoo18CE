# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wizard_default_product_id = fields.Many2one(
        'product.product',
        'Producto por defecto para la producción',
        config_parameter='mrp_group_by_category.default_product_id',
        help="Este producto se cargará por defecto en el asistente de fabricación."
    ) 