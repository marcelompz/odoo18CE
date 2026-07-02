# -*- coding: utf-8 -*-
"""
Created on 2026-01-12 17:19:26

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductPackagingInherit(models.Model):
    _inherit = 'product.packaging'

    linear_meter = fields.Float(
        string='Metro lineal')
