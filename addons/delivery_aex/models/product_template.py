# -*- coding: utf-8 -*-
"""
Created on 2025-07-02 17:28:35

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

    aex_product_length = fields.Float(
        string='Largo (cm)')
    aex_product_high = fields.Float(
        string='Alto (cm)')
    aex_product_width = fields.Float(
        string='Ancho (cm)')


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    aex_product_length = fields.Float(
        string='Largo (cm)',
        related='product_tmpl_id.aex_product_length',
        store=True,
        readonly=False)

    aex_product_high = fields.Float(
        string='Alto (cm)',
        related='product_tmpl_id.aex_product_high',
        store=True,
        readonly=False)

    aex_product_width = fields.Float(
        string='Ancho (cm)',
        related='product_tmpl_id.aex_product_width',
        store=True,
        readonly=False)
