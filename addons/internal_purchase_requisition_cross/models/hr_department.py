# -*- coding: utf-8 -*-
"""
Created on 2025-12-03 11:54:02

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrDepartmentInherit(models.Model):
    _inherit = 'hr.department'

    department_product_ids = fields.Many2many(
        'product.product', string='Lista de Productos', relation='hr_department_product_rel', column1='department_id', column2='product_id', domain=[('purchase_ok', '=', True)])
    product_count = fields.Integer(
        string='Conteo de Productos', compute='_compute_product_count')

    @api.depends('department_product_ids')
    def _compute_product_count(self):
        for record in self:
            record.product_count = len(record.department_product_ids)
