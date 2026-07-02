# -*- coding: utf-8 -*-
"""
Created on 2025-02-11 09:12:39

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    employee_signature = fields.Binary(
        string='Firma digital', copy=False)
    employee_sign_initials = fields.Binary(
        string='Iniciales digitales', copy=False)
