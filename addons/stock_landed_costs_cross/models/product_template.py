# -*- coding: utf-8 -*-
"""
Created on 2025-03-26 09:42:16

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    landed_cost_percentage = fields.Float(
        string='Costo % de la factura')
    margin_gain = fields.Float(
        string='Margen', help='Margen de ganancia para el precio de venta', copy=False)
