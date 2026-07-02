# -*- coding: utf-8 -*-
"""
Created on 2026-02-25 13:40:09

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DelinquentCustomerReportCross(models.TransientModel):
    _name = 'delinquent.customer.report.cross'
    _description = 'Reporte de clientes morosos'

    partner_id = fields.Many2one(
        'res.partner', string='Cliente')
    date_from = fields.Date(
        string='Fecha desde')
    date_to = fields.Date(
        string='Fecha hasta')
    show_only_expired = fields.Boolean(
        string="Mostrar solo vencidos")
    line_ids = fields.One2many(
        'delinquent.customer.report.line.cross', 'report_id', string='Líneas del reporte')

    def action_done(self):
        if not self.date_from:
            today = fields.Date.context_today(self)
            self.date_from = today.replace(month=1, day=1)

        if not self.date_to:
            self.date_to = fields.Date.context_today(self)

        domain = [
            ('invoice_date', '>=', self.date_from),     # fecha desde
            ('invoice_date', '<=', self.date_to),       # fecha hasta
            ('move_type', '=', 'out_invoice'),          # facturas de clientes
            ('state', '=', 'posted'),                   # facturas confirmadas
            ('amount_residual', '>', 0),                # saldo a pagar > 0
        ]

        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        if self.show_only_expired:
            domain.append(('invoice_date_due', '<', self.date_to))
        
        invoices = self.env['account.move'].search(domain, order='partner_id')

        self.line_ids.unlink()

        lines = []
        for invoice in invoices:
            lines.append(Command.create({
                'partner_id': invoice.partner_id.id,
                'invoice_id': invoice.id,
            }))

        self.line_ids = lines

        return self.env.ref('utex_account_cross.action_delinquent_customer_report').report_action(self)


class DelinquentCustomerReportCross(models.TransientModel):
    _name = 'delinquent.customer.report.line.cross'
    _description = 'Línea del reporte de clientes morosos'

    report_id = fields.Many2one(
        'delinquent.customer.report.cross')
    partner_id = fields.Many2one(
        'res.partner', string='Cliente')
    invoice_id = fields.Many2one(
        'account.move', string='Factura')
    invoice_number = fields.Char(
        related='invoice_id.invoice_number')
    invoice_date = fields.Date(
        related='invoice_id.invoice_date')
    currency_id = fields.Many2one(
        related='invoice_id.company_currency_id')
    amount_total_signed = fields.Monetary(
        related='invoice_id.amount_total_signed')
    amount_residual_signed = fields.Monetary(
        related='invoice_id.amount_residual_signed')
