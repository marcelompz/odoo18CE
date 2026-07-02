# -*- coding: utf-8 -*-
"""
Created on 2026-02-03 11:21:57

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    note = fields.Text(
        string='Observaciones', help='Observaciones de la transacción')
    origin_bank_id = fields.Many2one(
        'res.bank', string='Banco de origen')
    account_holder = fields.Char(
        string='Títular')
    operation_number = fields.Char(
        string='Número de operación')
