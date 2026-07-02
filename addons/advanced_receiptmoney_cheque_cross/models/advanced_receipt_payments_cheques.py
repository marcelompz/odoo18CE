# -*- coding: utf-8 -*-
"""
Created on 2025-07-31 13:28:15

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AdvancedReceiptPaymentsInherit(models.Model):
    _inherit = 'advanced.receipt.payments'

    cheque_ids = fields.Many2many(
        'account.cheque.payment')
    cheque_total_amount = fields.Monetary(
        string='Total de cheques', compute='_compute_totals_amounts', currency_field='currency_id')
    customer_cheques_domain = fields.Char(
        string="Dominio de Cheques",
        compute='_compute_customer_cheque_domain',
        store=False,
    )

    @api.depends('partner_id', 'invoice_ids')
    def _compute_customer_cheque_domain(self):
        for rec in self:
            if not rec.partner_id or not rec.invoice_ids:
                rec.customer_cheques_domain = "[('id', '=', 0)]"
                # Es buena práctica limpiar los cheques también
                rec.cheque_ids = [(5, 0, 0)]
                continue

            # 1. Encontrar IDs de cheques ya usados en otros recibos no cancelados.
            #    Asumo que 'receipt_payment_id' es un campo que añadiste a 'account.cheque.payment'.
            used_cheque_ids = self.env['advanced.receipt.payments'].search([
                ('id', '!=', rec.id or rec._origin.id),
                ('state', '!=', 'canceled'),
            ]).cheque_ids.ids

            # 2. Construir el dominio estricto.
            domain = [
                ('partner_id', 'child_of', rec.partner_id.id),
                ('state', 'in', ['paid', 'done', 'registered', 'deposited']),
                ('payment_type', '=', 'receive_money'),
                
                # Excluir los cheques ya usados
                ('id', 'not in', used_cheque_ids),
                
                # Filtrar ESTRICTAMENTE por cheques vinculados a las facturas seleccionadas.
                # Asumo que el campo se llama 'invoice_ids' en el modelo 'account.cheque.payment'.
                # Si se llama diferente, ajústalo aquí.
                ('invoice_ids', 'in', rec.invoice_ids.ids)
            ]
            
            rec.customer_cheques_domain = str(domain)

    @api.depends('invoice_ids', 'payment_ids', 'credit_note_ids', 'cheque_ids')
    def _compute_totals_amounts(self):
        """Hereda del principal y además computa los montos de cheques"""

        # Llamar al método padre para asegurar cálculos previos
        super()._compute_totals_amounts()

        for rec in self:
            # Calculamos el total de cheques
            rec.cheque_total_amount = sum(line.payment_amount for line in rec.cheque_ids)

            # Sumamos el total de cheques al total general
            rec.total_amount += rec.cheque_total_amount  # <- Modificamos directamente el campo

    def action_done(self):
        # Llamamos al método original para mantener la lógica existente
        res = super().action_done()

        # Validamos que haya al menos un pago o un cheque
        if not self.payment_ids and not self.cheque_ids:
            raise ValidationError(_('Debe seleccionar al menos un pago o un cheque para generar el recibo de dinero!'))

        # Registramos los cheques si están en estado 'draft'
        for cheque in self.cheque_ids:
            if cheque.cheque_id.state == 'draft':
                cheque.cheque_id.action_register()
                cheque.cheque_id.action_skip_steps()

            cheque.receipt_payment_id = self.id

        return res

    def action_cancel(self):
        res = super().action_cancel()
        
        for cheque in self.cheque_ids:
            cheque.cheque_id.action_cancel()
            cheque.cheque_id.receipt_payment_id = False
                
        return res
