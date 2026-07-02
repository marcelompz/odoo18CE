# -*- coding: utf-8 -*-
"""
Created on 2025-07-29 11:37:50

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    add_employee_signature = fields.Boolean(
        string='Agregar firma de empleado', default=False)


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    module_advanced_receiptmoney_signature_cross = fields.Boolean(
        related='company_id.add_employee_signature', readonly=False)
