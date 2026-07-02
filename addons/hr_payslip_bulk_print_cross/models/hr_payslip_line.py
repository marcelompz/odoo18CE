# -*- coding: utf-8 -*-
from odoo import fields, models


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    appears_on_internal_payslip = fields.Boolean(
        string='Aparece en recibo interno',
        related='salary_rule_id.appears_on_internal_payslip',
        store=True,
        readonly=True,
        help='Replicado desde la regla salarial. Controla si la línea '
             'aparece en el reporte MTESS interno.',
    )
