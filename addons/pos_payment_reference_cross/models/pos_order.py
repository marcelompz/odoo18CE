# -*- coding: utf-8 -*-
"""
Created on 2026-03-10 16:54:47

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    payment_references = fields.Char(
        string="Referencias de Pago",
        compute="_compute_payment_references",
        store=True,
        help="Muestra todas las referencias de los pagos realizados en este pedido."
    )

    @api.depends('payment_ids.transaction_reference')
    def _compute_payment_references(self):
        for order in self:
            # Obtenemos todas las referencias que no estén vacías
            refs = order.payment_ids.filtered(lambda p: p.transaction_reference).mapped('transaction_reference')
            
            if refs:
                # Eliminamos duplicados si los hubiera y unimos con |
                unique_refs = list(dict.fromkeys(refs)) 
                order.payment_references = " | ".join(unique_refs)
            
            else:
                order.payment_references = ""
