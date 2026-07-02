# -*- coding: utf-8 -*-
"""Extension de hr.employee para mostrar el historial de pagos como
pestana en el formulario, con resumen de cada recibo (dias, horas,
ingresos, descuentos, neto desembolsado).
"""
from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    cn_payslip_history_ids = fields.One2many(
        'hr.payslip', 'employee_id',
        string='Historial de Recibos',
        domain=[('state', 'in', ['done', 'paid', 'verify'])],
    )
    cn_payslip_count = fields.Integer(
        string='Cantidad de recibos',
        compute='_compute_cn_payslip_totals',
    )
    cn_total_paid_lifetime = fields.Monetary(
        string='Total desembolsado historico',
        compute='_compute_cn_payslip_totals',
        currency_field='cn_currency_id',
    )
    cn_currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        compute='_compute_cn_currency_id', store=False,
    )

    def _compute_cn_currency_id(self):
        for emp in self:
            emp.cn_currency_id = (emp.company_id.currency_id
                                  or self.env.company.currency_id)

    def _compute_cn_payslip_totals(self):
        Payslip = self.env['hr.payslip'].sudo()
        for emp in self:
            slips = Payslip.search([
                ('employee_id', '=', emp.id),
                ('state', 'in', ['done', 'paid']),
            ])
            emp.cn_payslip_count = len(slips)
            emp.cn_total_paid_lifetime = sum(slips.mapped('cn_total_neto'))
