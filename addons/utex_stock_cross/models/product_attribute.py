# -*- coding: utf-8 -*-
"""
Created on 2025-12-15 20:28:58

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductAttributeInherit(models.Model):
    _inherit = 'product.attribute'

    field_related = fields.Selection(
        string='Campo relacionado', selection=[('color', 'Color'),])


class ProductAttributeValueInherit(models.Model):
    _inherit = 'product.attribute.value'

    field_related = fields.Selection(
        related='attribute_id.field_related')
