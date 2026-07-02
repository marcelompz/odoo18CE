# -*- coding: utf-8 -*-
"""
Created on 2026-03-23 13:54:01

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AdvancedReceiptPaymentsInherit(models.Model):
    _inherit = 'advanced.receipt.payments'

    @api.depends('partner_id', 'invoice_ids', 'payment_ids')
    def _compute_customer_payments_domain(self):
        for rec in self:
            # Si no hay cliente, limpiamos todo
            if not rec.partner_id:
                rec.customer_payments_domain = "[('id', '=', 0)]"
                rec.payment_ids = [(5, 0, 0)]
                continue

            # CASO ANTICIPO: Si no hay facturas pero YA HAY un pago asignado
            # (Evitamos que el código base lo borre)
            if not rec.invoice_ids and rec.payment_ids:
                rec.customer_payments_domain = str([('id', 'in', rec.payment_ids.ids)])
                continue

            # CASO CREACIÓN MANUAL O CON FACTURAS
            if not rec.invoice_ids:
                rec.customer_payments_domain = "[('id', '=', 0)]"
                # Solo borramos si el registro no tiene ID (es nuevo y no viene de un anticipo)
                if not rec.id:
                    rec.payment_ids = [(5, 0, 0)]
                continue

            # Si llegamos aquí, hay facturas. Buscamos pagos conciliados.
            domain = [
                ('partner_id', 'child_of', rec.partner_id.id),
                ('state', 'in', ['paid', 'in_progress']),
                ('payment_type', '=', 'inbound'),
                ('reconciled_invoice_ids', 'in', rec.invoice_ids.ids)
            ]
            rec.customer_payments_domain = str(domain)
