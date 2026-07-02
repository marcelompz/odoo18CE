# -*- coding: utf-8 -*-
"""
Created on 2026-02-06 11:28:14

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    transaction_reference = fields.Char(string="Referencia de Pago")
