# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    outstanding_debt = fields.Monetary(
        string='Saldo Pendiente',
        compute='_compute_outstanding_debt',
        currency_field='company_currency_id',
        depends=['invoice_ids.state', 'invoice_ids.amount_residual'],
    )

    company_currency_id = fields.Many2one(
        'res.currency', 
        compute='_compute_company_currency_id', 
        store=True,
    )

    @api.depends('company_id')
    def _compute_company_currency_id(self):
        for partner in self:
            partner.company_currency_id = partner.company_id.currency_id or self.env.company.currency_id

    def _credit_debit_get(self):
        """
        Sobrescribimos el método core de Odoo con un bloque try/except
        para evitar el error TypeError: bad operand type for unary -: 'NoneType'
        """
        try:
            return super(ResPartner, self)._credit_debit_get()
        except TypeError:
            # Si el core de Odoo explota por un NoneType, asignamos 0 manualmente
            for partner in self:
                partner.debit = 0.0
                partner.credit = 0.0
            return True

    @api.depends('invoice_ids', 'move_line_ids')
    def _compute_outstanding_debt(self):
        for partner in self:
            partner_c = partner.with_company(self.env.company)
            accounting_balance = 0.0
            try:
                # Omitimos el uso de partner_c.debit y partner_c.credit directo 
                # porque Odoo puede mantener el caché de un company_id diferente 
                # (ej. test1) si el partner se cargó antes en la misma transacción RPC.
                # Calculamos el balance de la cuenta a cobrar manualmente:
                account_id = partner_c.property_account_receivable_id
                if account_id:
                    self.env.cr.execute("""
                        SELECT SUM(debit) - SUM(credit)
                        FROM account_move_line
                        WHERE partner_id = %s AND account_id = %s AND reconciled = False
                    """, (partner.id, account_id.id))
                    res = self.env.cr.fetchone()
                    accounting_balance = res[0] or 0.0
            except Exception as e:
                _logger.error("Fallo en cálculo contable manual para partner %s: %s", partner.id, e)
                accounting_balance = 0.0

            pos_orders = self.env['pos.order'].search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['paid', 'done', 'draft']), # draft orders might be pending in session
                ('session_id.state', '!=', 'closed')
            ])
            
            pos_debt_delta = 0.0
            for order in pos_orders:
                if order.account_move and order.account_move.state == 'posted':
                    continue # Already in accounting_balance
                
                compensating_move = self.env['account.move'].search([
                    ('ref', 'ilike', f'%{order.name}%'),
                    ('state', '=', 'posted')
                ], limit=1)
                if compensating_move:
                    continue # Already in accounting_balance

                real_paid = sum(order.payment_ids.filtered(
                    lambda p: p.payment_method_id.type in ['cash', 'bank']
                ).mapped('amount'))
                
                # Exclude debt settlement product from order total to calculate true debt delta
                settlement_amount = sum(order.lines.filtered(
                    lambda l: l.product_id.name == 'Abono de Cuenta'
                ).mapped('price_subtotal_incl'))
                
                real_amount_total = order.amount_total - settlement_amount
                pos_debt_delta += (real_amount_total - real_paid)

            total_due = accounting_balance + pos_debt_delta
            partner.outstanding_debt = -total_due

            _logger.info(
                "--- OUTSTANDING DEBT CALCULATION PARA %s ---\n"
                "Accounting balance: %s\n"
                "POS Orders Encontradas: %s\n"
                "POS Debt Delta: %s\n"
                "Total Due: %s\n"
                "Outstanding Debt: %s",
                partner.name, accounting_balance, pos_orders.ids, pos_debt_delta, total_due, partner.outstanding_debt
            )

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        res += ['outstanding_debt', 'company_currency_id']
        return res
