# -*- coding: utf-8 -*-
"""
Extension de hr.payslip para Paraguay:
- hours_holiday_day_worked: horas DIURNAS trabajadas en feriados del periodo
- hours_holiday_night_worked: horas NOCTURNAS trabajadas en feriados del periodo

La deteccion de "feriado" usa resource.calendar.leaves de la compañia/calendario
(donde se cargan los dias feriados oficiales).

Si el modulo hr_attendance_shift_groups esta instalado, usa los campos
hours_extra_day y hours_extra_night por asistencia para discriminar diurno
de nocturno con precision. Si no, considera todo como diurno.
"""
from datetime import datetime, time, timedelta
import logging

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    hours_holiday_day_worked = fields.Float(
        string='Horas diurnas en feriado',
        compute='_compute_holiday_hours',
        store=True,
        digits=(8, 2),
        help='Horas trabajadas en dias feriados del periodo, '
             'en franja diurna.',
    )
    hours_holiday_night_worked = fields.Float(
        string='Horas nocturnas en feriado',
        compute='_compute_holiday_hours',
        store=True,
        digits=(8, 2),
        help='Horas trabajadas en dias feriados del periodo, '
             'en franja nocturna.',
    )

    @api.depends('employee_id', 'date_from', 'date_to', 'contract_id')
    def _compute_holiday_hours(self):
        Calendar = self.env['resource.calendar.leaves'].sudo()
        Attendance = self.env['hr.attendance'].sudo()

        # Detectar si tenemos los campos de shift_groups
        has_shift_fields = (
            'hours_extra_day' in Attendance._fields
            and 'hours_extra_night' in Attendance._fields
        )

        for slip in self:
            slip.hours_holiday_day_worked = 0.0
            slip.hours_holiday_night_worked = 0.0
            if not (slip.employee_id and slip.date_from and slip.date_to):
                continue

            # 1) Encontrar feriados que caen dentro del periodo
            #    resource.calendar.leaves sin resource_id (afectan todos)
            #    o asignados al calendario del empleado.
            calendar = (
                slip.contract_id.resource_calendar_id
                if slip.contract_id and slip.contract_id.resource_calendar_id
                else slip.employee_id.resource_calendar_id
            )

            holiday_domain = [
                ('date_from', '<=', datetime.combine(slip.date_to, time.max)),
                ('date_to', '>=', datetime.combine(slip.date_from, time.min)),
                ('resource_id', '=', False),  # solo globales
            ]
            if calendar:
                holiday_domain += ['|',
                                   ('calendar_id', '=', calendar.id),
                                   ('calendar_id', '=', False)]
            holidays = Calendar.search(holiday_domain)
            if not holidays:
                continue

            # Set de fechas (date) cubiertas por feriados
            holiday_dates = set()
            for h in holidays:
                hf = h.date_from
                ht = h.date_to
                if not hf or not ht:
                    continue
                d = hf.date()
                end = ht.date()
                while d <= end:
                    if slip.date_from <= d <= slip.date_to:
                        holiday_dates.add(d)
                    d += timedelta(days=1)

            if not holiday_dates:
                continue

            # 2) Obtener marcaciones del empleado en esas fechas
            tz_name = slip.employee_id.tz or 'UTC'
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC

            day_total = 0.0
            night_total = 0.0
            for day in holiday_dates:
                day_start_local = datetime.combine(day, time(0, 0))
                day_end_local = datetime.combine(day, time(23, 59, 59))
                day_start_utc = tz.localize(day_start_local).astimezone(pytz.utc).replace(tzinfo=None)
                day_end_utc = tz.localize(day_end_local).astimezone(pytz.utc).replace(tzinfo=None)
                atts = Attendance.search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('check_in', '>=', day_start_utc),
                    ('check_in', '<=', day_end_utc),
                ])
                if not atts:
                    continue
                if has_shift_fields:
                    day_total += sum(atts.mapped('hours_extra_day') or [0])
                    night_total += sum(atts.mapped('hours_extra_night') or [0])
                    # Si todo viene en cero (puede pasar antes del recompute),
                    # caer al worked_hours como diurno
                    if not (day_total or night_total):
                        day_total += sum(atts.mapped('worked_hours') or [0])
                else:
                    # Sin shift_groups: todo a diurno
                    day_total += sum(atts.mapped('worked_hours') or [0])

            slip.hours_holiday_day_worked = round(day_total, 2)
            slip.hours_holiday_night_worked = round(night_total, 2)
