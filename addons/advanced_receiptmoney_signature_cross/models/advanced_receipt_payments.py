# -*- coding: utf-8 -*-
"""
Created on 2025-02-11 09:12:07

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AdvancedReceiptPaymentsInherit(models.Model):
    _inherit = 'advanced.receipt.payments'

    employee_id = fields.Many2one(
        'hr.employee', string='Firmado por', copy=False)
    employee_signature = fields.Image(
        related='employee_id.employee_signature')
