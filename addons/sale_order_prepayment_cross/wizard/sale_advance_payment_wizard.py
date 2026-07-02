# -*- coding: utf-8 -*-
"""
Created on 2025-08-15 15:28:42

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentWizard(models.TransientModel):
    _name = 'sale.advance.payment.wizard'
    _description = 'Wizard de Anticipo en Venta'

    sale_order_id = fields.Many2one(
        'sale.order', required=True)
    amount = fields.Monetary(
        string='Monto del Anticipo', required=True)
    currency_id = fields.Many2one(
        'res.currency', required=True)
    journal_id = fields.Many2one(
        'account.journal', string='Diario de Pago', required=True, domain="[('type', 'in', ('bank', 'cash'))]")
    payment_date = fields.Date(
        string='Fecha de Pago', default=fields.Date.context_today, required=True)

    def action_create_payment(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("El monto del pago debe ser positivo."))

        # Opcion 1: Crea el pago y luego se debe conciliar con la factura
        if not self.env.company.prepayment_auto_reconcile:
            # Crear el pago
            payment = self.env['account.payment'].create({
                'date': self.payment_date,
                'amount': self.amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.sale_order_id.partner_id.id,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id.id,
                'memo': _('Anticipo para %s') % self.sale_order_id.name,
                'sale_order_id': self.sale_order_id.id,
            })
            
            # Confirmar el pago
            payment.action_post()

            # Llamar a la lógica de procesamiento en la orden de venta
            self.sale_order_id._process_prepayment(payment)

        else:
            # Opcion 2: Crear el pago y conciliarlo directamente con la factura
            # Se prepara el diccionario de datos del pago
            payment_data ={
                'date': self.payment_date,
                'amount': self.amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.sale_order_id.partner_id.id,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id.id,
                'memo': _('Anticipo para %s') % self.sale_order_id.name,
                'sale_order_id': self.sale_order_id.id,
            }
            
            # Llamar a la lógica de procesamiento en la orden de venta
            self.sale_order_id._process_prepayment(payment_data)
        
        return {'type': 'ir.actions.act_window_close'}
