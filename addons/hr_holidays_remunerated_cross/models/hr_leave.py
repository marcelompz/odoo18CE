# -*- coding: utf-8 -*-
"""
hr.leave extensions:
- is_remunerated boolean
- Al validar: crea/marca asistencias por dia.
- Boton manual "Aplicar a Asistencias" en cualquier estado para forzar
  el procesamiento (util para licencias validadas antes de instalar este
  modulo o para re-aplicar despues de cambios).
"""
import logging
from datetime import timedelta, time, datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    is_remunerated = fields.Boolean(
        string='Es remunerado',
        default=True,
        tracking=True,
    )
    leave_attendance_count = fields.Integer(
        string='Asistencias generadas',
        compute='_compute_leave_attendance_count',
    )

    @api.depends('state')
    def _compute_leave_attendance_count(self):
        Att = self.env['hr.attendance'].sudo()
        for rec in self:
            rec.leave_attendance_count = Att.search_count([('leave_id', '=', rec.id)])

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_default_remunerated(self):
        for rec in self:
            if rec.holiday_status_id and 'is_remunerated_default' in rec.holiday_status_id._fields:
                rec.is_remunerated = rec.holiday_status_id.is_remunerated_default

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'is_remunerated' not in vals and vals.get('holiday_status_id'):
                lt = self.env['hr.leave.type'].browse(vals['holiday_status_id'])
                if lt and 'is_remunerated_default' in lt._fields:
                    vals['is_remunerated'] = lt.is_remunerated_default
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Hooks de transicion
    # ------------------------------------------------------------------
    def action_validate(self, *args, **kwargs):
        res = super().action_validate(*args, **kwargs)
        for leave in self.filtered(lambda l: l.state == 'validate'):
            try:
                leave._apply_leave_to_attendances()
            except Exception as e:
                _logger.exception(
                    "Error aplicando licencia %s a asistencias: %s",
                    leave.display_name, e,
                )
        return res

    def action_refuse(self, *args, **kwargs):
        for leave in self.filtered(lambda l: l.state == 'validate'):
            try:
                leave._unapply_leave_from_attendances()
            except Exception as e:
                _logger.exception(
                    "Error removiendo licencia %s de asistencias: %s",
                    leave.display_name, e,
                )
        return super().action_refuse(*args, **kwargs)

    # ------------------------------------------------------------------
    # Boton manual: aplicar a asistencias (re-procesar)
    # ------------------------------------------------------------------
    def action_manual_apply_attendances(self):
        """Boton del formulario: fuerza el (re)procesamiento de la
        licencia sobre las asistencias del rango."""
        for leave in self:
            if leave.state != 'validate':
                raise UserError(_(
                    'La solicitud "%s" debe estar Validada para aplicarla a '
                    'asistencias. Estado actual: %s'
                ) % (leave.display_name, leave.state))
            leave._apply_leave_to_attendances()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Listo'),
                'message': _('Asistencias actualizadas para %d licencia(s).') % len(self),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_leave_attendances(self):
        """Smart button: ver las asistencias asociadas."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asistencias generadas'),
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [('leave_id', '=', self.id)],
            'context': {'default_leave_id': self.id},
        }

    # ------------------------------------------------------------------
    # Logica principal
    # ------------------------------------------------------------------
    def _get_employee_tz(self):
        self.ensure_one()
        tz_name = self.employee_id.tz or self.env.user.tz or 'UTC'
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _iter_leave_days(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            return
        tz = self._get_employee_tz()
        df = self.date_from
        dt = self.date_to
        if df.tzinfo is None:
            df = pytz.utc.localize(df)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        start_local = df.astimezone(tz).date()
        end_local = dt.astimezone(tz).date()
        d = start_local
        while d <= end_local:
            yield d
            d += timedelta(days=1)

    def _apply_leave_to_attendances(self):
        Attendance = self.env['hr.attendance'].sudo()
        for leave in self:
            if not leave.employee_id or not leave.date_from or not leave.date_to:
                _logger.warning(
                    "Licencia %s sin empleado o fechas; saltando.", leave.display_name
                )
                continue
            tz = leave._get_employee_tz()
            type_name = leave.holiday_status_id.name or _('Licencia')
            created = updated = 0
            for day in leave._iter_leave_days():
                day_start_local = datetime.combine(day, time(0, 0))
                day_end_local = datetime.combine(day, time(23, 59, 59))
                day_start_utc = tz.localize(day_start_local).astimezone(pytz.utc).replace(tzinfo=None)
                day_end_utc = tz.localize(day_end_local).astimezone(pytz.utc).replace(tzinfo=None)

                existing = Attendance.search([
                    ('employee_id', '=', leave.employee_id.id),
                    ('check_in', '>=', day_start_utc),
                    ('check_in', '<=', day_end_utc),
                ], limit=1)

                vals_common = {
                    'leave_id': leave.id,
                    'is_leave_attendance': True,
                    'leave_is_remunerated': leave.is_remunerated,
                    'leave_type_name': type_name,
                    'unremunerated_absence': not leave.is_remunerated,
                    'unremunerated_leave_id': leave.id if not leave.is_remunerated else False,
                }
                if existing:
                    existing.write(vals_common)
                    updated += 1
                else:
                    cin_local = datetime.combine(day, time(9, 0))
                    cout_local = datetime.combine(day, time(17, 0))
                    cin_utc = tz.localize(cin_local).astimezone(pytz.utc).replace(tzinfo=None)
                    cout_utc = tz.localize(cout_local).astimezone(pytz.utc).replace(tzinfo=None)
                    vals = {
                        'employee_id': leave.employee_id.id,
                        'check_in': cin_utc,
                        'check_out': cout_utc,
                    }
                    vals.update(vals_common)
                    Attendance.create(vals)
                    created += 1
            _logger.info(
                "Licencia %s: %d asistencias creadas, %d actualizadas.",
                leave.display_name, created, updated,
            )

    def _unapply_leave_from_attendances(self):
        Attendance = self.env['hr.attendance'].sudo()
        for leave in self:
            atts = Attendance.search([('leave_id', '=', leave.id)])
            atts.write({
                'leave_id': False,
                'is_leave_attendance': False,
                'leave_is_remunerated': False,
                'leave_type_name': False,
                'unremunerated_absence': False,
                'unremunerated_leave_id': False,
            })

    def _get_unremunerated_days(self):
        self.ensure_one()
        if not self.is_remunerated:
            return self.number_of_days or 0.0
        return 0.0
