# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 22:35:14

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    internal_type = fields.Selection(
        selection_add=[
            ('invoice', 'Facturas'),
            ('invoice_in', 'Facturas de compra'),
            ('debit_note', 'Notas de débito'),
            ('credit_note', 'Notas de crédito'),
            ('receipt_invoice', 'Factura de recibo'),
            ('stock_picking', 'Entrega de stock'),
        ],
    )
