# -*- coding: utf-8 -*-
"""
Created on 2026-02-03 11:22:47

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPaymentRegisterInherit(models.TransientModel):
    _inherit = 'account.payment.register'

    note = fields.Text(
        string='Observaciones', help='Observaciones de la transacción')
    origin_bank_id = fields.Many2one(
        'res.bank', string='Banco de origen')
    account_holder = fields.Char(
        string='Títular')
    operation_number = fields.Char(
        string='Número de operación')
    journal_type = fields.Selection(
        related='journal_id.type')

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result)

        res.update({
            'note': self.note or False,
            'origin_bank_id': self.origin_bank_id.id or False,
            'account_holder': self.account_holder or False,
            'operation_number': self.operation_number or False,
        })

        return res
