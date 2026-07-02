# -*- coding: utf-8 -*-
"""
Created on 2025-03-26 10:26:29

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductCategoryInherit(models.Model):
    _inherit = 'product.category'

    margin_gain = fields.Float(
        string='Margen', help='Margen de ganancia para el precio de venta', copy=False)
