# -*- coding: utf-8 -*-
"""
Created on 2025-07-29 11:37:37

@author: drojo
"""
# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    receipt_payment_id = fields.Many2one(
        'advanced.receipt.payments', string='Recibo de dinero')
    count_receipt_payments = fields.Integer(
        string='Contador de recibos de dinero', compute='_compute_count_receipt_payments')
    concept = fields.Char(
        string='Concepto de pago')

    @api.depends('receipt_payment_id')
    def _compute_count_receipt_payments(self):
        for rec in self:
            rec.count_receipt_payments = len(rec.receipt_payment_id)
    
    def action_create_receipt_payment(self):
        """
        Create a receipt payment and associate it with the current payment.
        """
        self.ensure_one()

        mixin = self.env['utils.common.mixin.cross']

        invoices = []
        payments = []

        for invoice in self.reconciled_invoice_ids:
            invoice_amount = invoice.amount_total
            
            if invoice.currency_id != self.currency_id:
                invoice_amount = invoice.currency_id._convert(
                    invoice.amount_total, self.currency_id, self.company_id, invoice.invoice_date)

            invoices.append(invoice.id)

        payments.append(self.id)

        payment = self.env['advanced.receipt.payments'].create({
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'total_amount': self.amount,
            'concept': self.concept,
            'state': 'draft',
            'invoice_ids': [Command.set(invoices)],
            'payment_ids': [Command.set(payments)],
        })

        if payment and mixin.check_installation('hr') and mixin.check_field_exists('account.payment', 'employee_id'):
            payment.update({
                'employee_id': self.employee_id.id,
            })

        try:
            self.receipt_payment_id = payment.id
            
            return self.button_open_receipt_payments()

        except Exception as e:
            raise UserError(_('Error al crear el recibo de dinero: %s' % e))

    def _get_amount_balance(self, invoice_payments):
        """
        Get the amount balance from the invoice payments.

        :param invoice_payments: Dictionary containing payment details.
        :return: Amount balance.
        :rtype: float
        """
        if not invoice_payments:
            return None

        total_amount = 0

        for line in invoice_payments.get('content', []):
            if line.get('account_payment_id'):
                partial = self.env['account.partial.reconcile'].browse(line.get('partial_id'))

                if partial.credit_currency_id == self.currency_id:
                    total_amount += partial.credit_amount_currency

                else:
                    total_amount += partial.credit_currency_id._convert(
                        partial.credit_amount_currency, self.currency_id, self.env.company, partial.create_date)

        return total_amount

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

    def action_create_receipt_payment_group(self):
        """
        Create a group of receipt payments for the selected payments.

        :return: Action to open the receipt payment group wizard.
        :rtype: dict
        :raises UserError: If payments are not from the same client or if a payment already has a receipt.
        """
        payments = self.search([('id', 'in', self.env.context.get('active_ids'))])
        if not payments:
            raise UserError(_('No se encontraron pagos.'))

        first_payment = payments[0]

        for payment in payments:
            if payment.partner_id != first_payment.partner_id:
                raise UserError(_('Los registros seleccionados deben ser del mismo cliente.'))
            if payment.receipt_payment_id:
                raise UserError(_('El pago seleccionado %s ya tiene un recibo de pago.' % payment.name))
            if payment.currency_id != first_payment.currency_id:
                raise UserError(_('¡Los pagos seleccionados deben realizarse en la misma moneda!'))

        view_id = self.env.ref('advanced_receiptmoney_cross.receipt_money_group_wizard_form')
        if view_id:
            return {
                'name': _('Generar recibo de dinero'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'receipt.money.group.wizard',
                'target': 'new',
                'view_id': view_id.id,
            }
        return {}
