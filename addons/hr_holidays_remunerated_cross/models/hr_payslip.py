# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    unremunerated_days = fields.Float(
        string='Dias no remunerados',
        compute='_compute_unremunerated_days',
        store=True,
        digits=(5, 2),
        help='Suma de dias de tiempo personal NO remunerado aprobado '
             'dentro del periodo del recibo. Se usa por la regla salarial '
             'PY_DESC_NO_REM para calcular el descuento del salario.',
    )

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_unremunerated_days(self):
        Leave = self.env['hr.leave'].sudo()
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                slip.unremunerated_days = 0.0
                continue
            leaves = Leave.search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', '=', 'validate'),
                ('is_remunerated', '=', False),
                ('date_from', '<=', slip.date_to),
                ('date_to', '>=', slip.date_from),
            ])
            slip.unremunerated_days = sum(l.number_of_days for l in leaves)
