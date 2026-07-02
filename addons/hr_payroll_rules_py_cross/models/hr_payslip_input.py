# -*- coding: utf-8 -*-
"""Extension de hr.payslip.input para agregar campo de moneda y mostrar
los importes con formato monetario en lugar de Float crudo.
"""
from odoo import api, fields, models


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    cn_currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        compute='_compute_cn_currency_id', store=False,
    )

    def _compute_cn_currency_id(self):
        for inp in self:
            inp.cn_currency_id = (
                inp.payslip_id.company_id.currency_id
                or inp.payslip_id.employee_id.company_id.currency_id
                or self.env.company.currency_id
            )
