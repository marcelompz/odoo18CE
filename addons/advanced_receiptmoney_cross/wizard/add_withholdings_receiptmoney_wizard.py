# -*- coding: utf-8 -*-
"""
Created on 2025-07-31 12:09:19

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AddWithholdingsReceiptmoneyWizard(models.TransientModel):
    _name = 'add.withholdings.receiptmoney.wizard'
    _description = 'Agrega retenciones al recibo de dinero'

    def _get_context_today(self):
        return fields.Date.context_today(self)

    receiptmoney_id = fields.Many2one(
        'advanced.receipt.payments', string='Recibo de dinero')
    move_id = fields.Many2one(
        'account.move', string='Factura')
    date = fields.Date(
        string='Fecha', default=_get_context_today)
    name = fields.Char(
        string='Número')
    payment_type = fields.Selection(
        string='Type', selection=[('payment', 'Pago'),('withholdings', 'Retención'),('others', 'Otros')], default='withholdings')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(
        string='Monto', currency_field='currency_id')
    journal_id = fields.Many2one(
        'account.journal', string='Diario')

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
    
        context = self._context
        copy_data = {
            'receiptmoney_id': context.get('receiptmoney_id'),
            'move_id': context.get('move_id'),
            'currency_id': context.get('currency_id', self.env.company.currency_id.id),
        }
        res.update(copy_data)
    
        return res

    def action_done(self):
        """
        Crea un nuevo pago (retención) y lo vincula al recibo de dinero.
        """
        self.ensure_one() # Aseguramos que trabajamos con un solo registro del wizard

        if not self.receiptmoney_id:
            raise UserError(_('No se encontró el recibo de dinero de origen. Por favor, cancele y vuelva a intentarlo.'))
        
        if not self.journal_id:
            raise ValidationError(_("Debe seleccionar un diario para la retención."))

        # 1. Preparar los valores para crear el nuevo registro de account.payment
        payment_vals = {
            'date': self.date,
            'amount': self.amount,
            'payment_type': 'inbound',
            'partner_id': self.move_id.partner_id.id,
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'memo': self.name or f"Retención Factura: {self.move_id.name}", # Referencia/Concepto
            # Opcional: Si quieres que el pago se vincule directamente a la factura
            # Esto intentará conciliarlo automáticamente al confirmar.
            'reconciled_invoice_ids': [(6, 0, [self.move_id.id])],
        }

        # 2. Crear el nuevo registro de account.payment
        new_payment = self.env['account.payment'].create(payment_vals)

        # Opcional pero recomendado: Confirmar el pago si es necesario.
        # Si el diario no tiene la confirmación manual, esto lo postea.
        if new_payment.state == 'draft':
            new_payment.action_post()
            
        # 3. Vincular el pago recién creado al recibo de dinero.
        # Usamos el comando mágico (4, id) que significa "añadir este ID a la relación".
        if new_payment:
            self.receiptmoney_id.write({
                'payment_ids': [(4, new_payment.id, 0)]
            })

        # Cerramos la ventana del wizard
        return {'type': 'ir.actions.act_window_close'}

    @api.constrains('amount')
    def _check_amount(self):
        """Valida que el monto sea mayor a cero."""
        if self.amount <= 0:
            raise ValidationError(_('El monto debe ser mayor a Cero.'))
