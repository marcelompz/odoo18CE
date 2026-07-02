# -*- coding: utf-8 -*-
"""
Created on 2025-12-18 15:21:05

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderTemplateInherit(models.Model):
    _inherit = 'sale.order.template'

    product_model_id = fields.Many2one(
        'product.model', string='Modelo del producto', ondelete='restrict')
