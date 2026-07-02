# -*- coding: utf-8 -*-
"""
Created on 2025-02-12 12:28:02

@author: drojo
"""
# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError


class AccountChequePaymentInherit(models.Model):
    _inherit = 'account.cheque.payment'

    receipt_payment_id = fields.Many2one(
        'advanced.receipt.payments', string='Recibo de dinero')
    count_receipt_payments = fields.Integer(
        string='Contador de recibos de dinero', compute='_compute_count_receipt_payments')

    @api.depends('receipt_payment_id')
    def _compute_count_receipt_payments(self):
        """
        Compute the count of associated receipt payments for this cheque payment.
        
        Sets
        ----
        count_receipt_payments : int
            Number of associated receipt payments.
        """
        for rec in self:
            if rec.receipt_payment_id:
                rec.count_receipt_payments = self.env['advanced.receipt.payments'].search_count([('id', '=', rec.receipt_payment_id.id)])
            else:
                rec.count_receipt_payments = 0

    def action_create_receipt_money(self):
        """
        Create a receipt payment and associate it with the current cheque payment.
        
        Returns
        -------
        dict
            An action dictionary for the receipt money message wizard or to open the receipt payments.
        """
        self.ensure_one()

        invoices = []
        payments = []

        for invoice in self.invoice_ids:
            # amount_payment = self._get_amount_balance(invoice.invoice_payments_widget)
            # invoice_amount = invoice.amount_total
            
            if invoice.currency_id != self.currency_id:
                invoice_amount = invoice.currency_id._convert(
                    invoice.amount_total, self.currency_id, self.company_id, invoice.invoice_date)

            invoices.append(invoice.id)

        payments.append(self.id)

        payment = self.env['advanced.receipt.payments'].create({
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'total_amount': self.payment_cheque_amount,
            'concept': self.memo,
            'state': 'draft',
            'invoice_ids': [Command.set(invoices)],
            'cheque_ids': [Command.set(payments)],
        })

        self.receipt_payment_id = payment.id

        return self.button_open_receipt_payments()

    def button_open_receipt_payments(self):
        """
        Redirect the user to the payment(s) paid by this payment.

        :return: An action on advanced.receipt.payments.
        :rtype: dict
        """
        self.ensure_one()

        action = {
            'name': _("Recibo de dinero"),
            'type': 'ir.actions.act_window',
            'res_model': 'advanced.receipt.payments',
            'context': {'create': False},
        }

        if len(self.receipt_payment_id) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.receipt_payment_id.id,
            })
        
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.receipt_payment_id.ids)],
            })
        
        return action

    def _get_amount_balance(self, invoice_payments):
        """
        Get the amount balance from the invoice payments.

        :param invoice_payments: Dictionary containing payment details.
        :return: Amount balance.
        :rtype: float
        """
        if not invoice_payments:
            return 0.0

        total_amount = 0.0

        for line in invoice_payments.get('content', []):
            if not line.get('account_payment_id'):
                partial = self.env['account.partial.reconcile'].browse(line.get('partial_id'))

                if 'Cheque' in partial.credit_move_id.name:
                    if partial.credit_currency_id == self.currency_id:
                        total_amount += partial.amount

                    else:
                        total_amount += partial.credit_currency_id._convert(
                        partial.amount, self.currency_id, self.env.company, partial.create_date)

        return total_amount

    def action_create_receipt_payment_group(self):
        payments = self.search([('id', 'in', self.env.context.get('active_ids'))])
        if not payments:
            raise UserError(_('No se encontraron pagos.'))

        first_payment = payments[0]

        for payment in payments:
            if payment.partner_id != first_payment.partner_id:
                raise UserError(_('Los registros seleccionados deben ser del mismo cliente.'))
            if payment.receipt_payment_id:
                raise UserError(_('El pago seleccionado %s ya tiene un recibo de pago.' % payment.name))
            if payment.currency_cheque_id != first_payment.currency_cheque_id:
                raise UserError(_('¡Los pagos seleccionados deben realizarse en la misma moneda!'))

        view_id = self.env.ref('advanced_receiptmoney_cheque_cross.cheque_receipt_money_group_wizard_form')
        if view_id:
            return {
                'name': _('Generar recibo de dinero'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cheque.receipt.money.group.wizard',
                'target': 'new',
                'view_id': view_id.id,
            }
        return {}
