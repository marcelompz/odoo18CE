# -*- coding: utf-8 -*-
"""Extension del Tablero Diario para mostrar el costo del dia segun el
tipo de contrato (mensualizado o jornalero).

Convenciones Paraguay:
- Mensualizado: salario / 30 (todos los dias del mes pagados, incluye
  fines de semana, feriados y descansos remunerados).
- Jornalero: salario / 26 (solo dias efectivamente trabajados).

El modo se determina por el tipo de contrato (hr.contract.type):
si tiene marcado "cn_is_jornalero" => jornalero; sino, mensualizado.
"""
from odoo import api, fields, models


class HrAttendanceDailyReport(models.Model):
    _inherit = 'hr.attendance.daily.report'

    daily_cost = fields.Monetary(
        string='Costo del dia (Gs.)',
        compute='_compute_daily_cost',
        currency_field='currency_id',
        help='Costo del dia segun el contrato.',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        compute='_compute_currency_id', store=False,
    )
    hours_total = fields.Float(
        string='Total Horas',
        compute='_compute_hours_total',
    )

    def _compute_currency_id(self):
        company = self.env.company
        for rec in self:
            rec.currency_id = (rec.employee_id.company_id.currency_id
                               or company.currency_id)

    def _compute_hours_total(self):
        for rec in self:
            rec.hours_total = (rec.total_ordinary or 0.0) + \
                              (rec.total_extra_day or 0.0) + \
                              (rec.total_extra_night or 0.0) + \
                              (rec.total_break or 0.0)

    @staticmethod
    def _is_jornalero_contract(contract):
        """Devuelve True si el contrato corresponde a un esquema jornalero."""
        if not contract:
            return False
        ct = contract.contract_type_id
        if not ct:
            return False
        if 'cn_is_jornalero' in ct._fields and ct.cn_is_jornalero:
            return True
        return False

    def _compute_daily_cost(self):
        for rec in self:
            contract = rec.employee_id.contract_id
            wage = (contract.wage if contract else 0.0) or 0.0
            if not wage:
                rec.daily_cost = 0.0
                continue

            is_jornalero = self._is_jornalero_contract(contract)
            divisor = 26.0 if is_jornalero else 30.0
            daily = wage / divisor
            hourly = daily / 8.0

            status = rec.absence_status or 'absence'
            cost = 0.0

            if is_jornalero:
                if status == 'present':
                    cost = daily
                    cost += (rec.total_extra_day or 0.0) * hourly * 0.5
                    cost += (rec.total_extra_night or 0.0) * hourly * (1.3 * 2.0 - 1.0)
            else:
                if status == 'absence':
                    cost = 0.0
                else:
                    cost = daily
                    if status == 'present':
                        cost += (rec.total_extra_day or 0.0) * hourly * 0.5
                        cost += (rec.total_extra_night or 0.0) * hourly * (1.3 * 2.0 - 1.0)
                    elif status == 'rest':
                        hours_worked = (rec.total_ordinary or 0.0) + \
                                       (rec.total_extra_day or 0.0) + \
                                       (rec.total_extra_night or 0.0)
                        if hours_worked > 0:
                            cost += hours_worked * hourly
            rec.daily_cost = cost
