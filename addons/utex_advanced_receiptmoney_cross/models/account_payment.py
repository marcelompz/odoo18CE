# -*- coding: utf-8 -*-
"""
Created on q

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    def action_create_receipt_payment(self):
        self.ensure_one()
        
        if self.receipt_payment_id:
            return self.button_open_receipt_payments()

        # En Odoo 18, para anticipos, reconciled_invoice_ids estará vacío []
        invoices = self.reconciled_invoice_ids.ids
        
        payment_receipt = self.env['advanced.receipt.payments'].create({
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'payment_date': self.date,
            'concept': self.concept or (f"ANTICIPO - {self.memo}" if self.memo else _("ANTICIPO DE CLIENTE")),
            'state': 'draft',
            'invoice_ids': [Command.set(invoices)],
            'payment_ids': [Command.set([self.id])],
        })

        self.receipt_payment_id = payment_receipt.id
        
        # Abrimos el recibo creado
        return {
            'name': _("Recibo de dinero"),
            'type': 'ir.actions.act_window',
            'res_model': 'advanced.receipt.payments',
            'view_mode': 'form',
            'res_id': payment_receipt.id,
            'target': 'current',
        }

    def button_open_receipt_payments(self):
        """
        Mantenemos la lógica de apertura pero aseguramos que 
        el contexto no bloquee la vista.
        """
        self.ensure_one()
        action = {
            'name': _("Recibo de dinero"),
            'type': 'ir.actions.act_window',
            'res_model': 'advanced.receipt.payments',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.receipt_payment_id.id,
        }
        return action
