# -*- coding: utf-8 -*-
"""
Created on 2025-08-15 15:22:44

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one(
        'sale.order', string='Orden de Venta de Origen', index=True, copy=False, help="Enlace al pedido de venta que originó este anticipo.")
