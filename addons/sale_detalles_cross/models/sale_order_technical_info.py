# -*- coding: utf-8 -*-
"""
Created on 2025-06-16 18:07:11

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderTechnicalInfoInherit(models.Model):
    _inherit = 'sale.order.technical.info'

    primary_color = fields.Char(
        string='Color Primario')
    secundary_color = fields.Char(
        string='Color Secundario')
    note = fields.Text(
        string='Observaciones')
