# -*- coding: utf-8 -*-
"""
Created on 2026-03-06 08:46:56

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    invoice_numbers_display = fields.Char(
        string='Nro. Factura', 
        compute='_compute_invoice_numbers_display', 
        store=True
    )

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.name')
    def _compute_invoice_numbers_display(self):
        for order in self:
            valid_invoices = order.invoice_ids.filtered(
                lambda m: m.state == 'posted' and m.move_type == 'in_invoice'
            )
            
            names = []
            for inv in valid_invoices:
                # Prioridad: invoice_number personalizado, luego name estándar
                num = getattr(inv, 'invoice_number', False) or inv.name
                if num:
                    names.append(num)
            
            order.invoice_numbers_display = ", ".join(set(names)) if names else ""
