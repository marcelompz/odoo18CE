# -*- coding: utf-8 -*-
"""
Created on 2025-12-04 13:39:25

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockMoveInherit(models.Model):
    _inherit = 'stock.move'

    product_length = fields.Float(
        string='Largo (Mts.)', digits='Product Unit of Measure')
    product_width = fields.Float(
        string='Ancho (Mts.)', digits='Product Unit of Measure')
    product_grammar = fields.Float(
        string='Gramatura (Grs.)', digits='Product Unit of Measure')
