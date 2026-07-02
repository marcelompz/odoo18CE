# -*- coding: utf-8 -*-
"""
Created on 2025-04-22 13:15:06

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

    coefficient_value = fields.Monetary(
        string='Coeficiente', currency_field='currency_id', copy=False)
    suggested_value = fields.Monetary(
        string='Valor sugerido', currency_field='currency_id', copy=False, help='Valor sugerido luego del calculo de costo promedio.')
