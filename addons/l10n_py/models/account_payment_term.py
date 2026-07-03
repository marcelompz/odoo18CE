# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 22:32:54

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPaymentTermInherit(models.Model):
    _inherit = "account.payment.term"

    is_cash_payment = fields.Boolean(
        string="Pago contado", help="Seleccionar sólo en el caso de ser una forma de pago al contado")
