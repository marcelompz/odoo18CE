# -*- coding: utf-8 -*-
"""
Created on 2025-02-11 14:14:52

@author: drojo
"""
# python
import pytz
from datetime import datetime

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ReceiptMoneyGroupWizard(models.TransientModel):
    _name = 'receipt.money.group.wizard'
    _inherit = 'utils.common.mixin.cross'
    _description = 'Generar recibo de dinero de un grupo de pagos'

    date = fields.Date(
        string='Date')
    partner_id = fields.Many2one(
        'res.partner', string='Partner')
    currency_id = fields.Many2one(
        'res.currency', string='Currency')
    old_currency_id = fields.Many2one(
        'res.currency', string='Currency')
    amount_total = fields.Monetary(
        string='Total amount')
    concept = fields.Char(
        string='Concept')
    move_ids = fields.Many2many(
        'account.move', string='Invoices')
    payment_ids = fields.Many2many(
        'account.payment', string='Payments')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        self.amount_total = self.old_currency_id._convert(
            self.amount_total, self.currency_id, self.env.company, self.date)
        self.old_currency_id = self.currency_id
    
    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
    
        context = self._context
        partner, currency, amount_total, concept, moves = self._get_group_data(context)
        copy_data = {
            'date': self.get_current_datetime('date'),
            'partner_id': partner.id,
            'currency_id': currency.id,
            'old_currency_id': currency.id,
            'amount_total': amount_total,
            'concept': concept,
            'move_ids': [(6,0, moves)],
            'payment_ids': [(6,0, context.get('active_ids'))]
        }
        res.update(copy_data)
    
        return res

    def _get_group_data(self, context):
        payments = self.env['account.payment'].search([('id', 'in', context.get('active_ids'))])
        partner = payments[0].partner_id
        currency = payments[0].currency_id
        amount_total = 0.0
        concept_set = set()
        moves_set = set()

        for payment in payments:
            for line in payment.reconciled_invoice_ids:
                concept_set.add((line.invoice_number or line.name) if self.check_field_exists(self, 'account.move', 'invoice_number') else line.name,)
                moves_set.add(line.id)
            
            if payment.currency_id == currency:
                amount_total += payment.amount

            else:
                amount_total += payment.currency_id._convert(
                    payment.amount, currency, payment.company_id, payment.date)

        concept = list(concept_set)
        moves = list(moves_set)
        concept_text = _('Pago por facturas %s' % ', '.join(concept))

        return partner, currency, amount_total, concept_text, moves

    def create_receipt_payment(self):
        self.ensure_one()

        invoices = []
        payments = []

        # invoices

        for invoice in self.move_ids:
            amount_payment = self._get_amount_balance(invoice.invoice_payments_widget)
            invoice_amount = invoice.amount_total

            if invoice.currency_id != self.currency_id:
                invoice_amount = invoice.currency_id._convert(
                    invoice.amount_total, self.currency_id, self.company_id, invoice.invoice_date)

            invoices.append((0, 0, {
                'invoice_date': invoice.invoice_date,
                'invoice_number': (invoice.invoice_number or invoice.name) if self.check_field_exists(self, 'account.move', 'invoice_number') else invoice.name,
                'date_due': invoice.invoice_date_due,
                'invoice_currency_id': invoice.currency_id.id,
                'amount_invoice_currency': invoice.amount_total,
                'payment_currency_id': self.currency_id.id,
                'invoice_amount_payment_currency': invoice_amount,
                'move_id': invoice.id,
                'amount_payment': amount_payment,
                'balance_payment': invoice_amount - amount_payment,
            }))

        # payments

        for line in self.payment_ids:
            payments.append((0, 0, {
                'date': line.date,
                'payment_number': line.name,
                'journal_id': line.journal_id.id,
                'currency_id': self.currency_id.id,
                'amount': line.amount if line.currency_id == self.currency_id else self._change_amount_currency(line.amount, line.currency_id, line.date),
                'payment_id': line.id,
                'move_id': line.reconciled_invoice_ids.id if len(line.reconciled_invoice_ids) == 1 else False,
            }))

        payment = self.env['advanced.receipt.payments'].create({
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'total_amount': self.amount_total,
            'concept': self.concept,
            'state': 'draft',
            'invoice_ids': invoices,
            'payment_ids': payments,
        })

        for line in self.payment_ids:
            line.receipt_payment_id = payment.id
        
        return self.button_open_receipt_payments(payment)

    def _change_amount_currency(self, amount, old_currency, date):
        return old_currency._convert(
            amount, self.currency_id, self.company_id, date)

    def _get_amount_balance(self, invoice_payments):
        """
        Get the amount balance from the invoice payments.

        :param invoice_payments: Dictionary containing payment details.
        :return: Amount balance.
        :rtype: float
        """
        if not invoice_payments:
            return None

        amount = 0.0

        for line in invoice_payments.get('content', []):
            if line.get('partial_id') and line.get('is_exchange') == False:
                partial = self.env['account.partial.reconcile'].browse(line.get('partial_id'))

                if not partial.full_reconcile_id:
                    if partial.debit_currency_id == self.currency_id:
                        amount += partial.debit_amount_currency

                    else:
                        amount += partial.debit_currency_id._convert(
                        partial.debit_amount_currency, self.currency_id, self.env.company, partial.create_date)
        
        return amount

    def button_open_receipt_payments(self, payment_id):

        action = {
            'name': _("Recibo de dinero"),
            'type': 'ir.actions.act_window',
            'res_model': 'advanced.receipt.payments',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': payment_id.id,
        }

        return action
