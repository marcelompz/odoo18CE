# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def _month_start(today):
    return today.replace(day=1)


def _month_end(today):
    if today.month == 12:
        return today.replace(day=31)
    nxt = today.replace(month=today.month + 1, day=1)
    return nxt - timedelta(days=1)


class HrAttendanceShiftRecompute(models.TransientModel):
    _name = 'hr.attendance.shift.recompute'
    _description = 'Wizard: Recalcular distribucion por franja en un periodo'

    date_from = fields.Date(
        string='Fecha desde', required=True,
        default=lambda self: _month_start(fields.Date.context_today(self)),
    )
    date_to = fields.Date(
        string='Fecha hasta', required=True,
        default=lambda self: _month_end(fields.Date.context_today(self)),
    )
    employee_ids = fields.Many2many('hr.employee', string='Empleados',
        help='Si se deja vacio, se aplica a todos los empleados con asistencia en el periodo.')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    shift_group_ids = fields.Many2many('hr.shift.group', string='Grupos de Turno')
    auto_assign_group = fields.Boolean(
        string='Asignar grupo de turno faltante', default=True,
        help='Si la asistencia no tiene grupo asignado, lo toma del empleado/contrato vigente.',
    )
    deep_clean = fields.Boolean(
        string='Limpieza profunda (recomendado)', default=True,
        help='Borra TODAS las lineas de distribucion del periodo antes de recalcular. '
             'Esto evita acumulacion de datos viejos cuando hay asistencias cruzadas o duplicadas.',
    )

    def action_recompute(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "desde" debe ser anterior a "hasta".'))
        Attendance = self.env['hr.attendance']
        domain = [
            ('check_in', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('check_in', '<=', fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)),
        ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))
        attendances = Attendance.search(domain)
        # Limpieza profunda: borrar TODAS las shift_lines con date en el rango,
        # incluyendo las que vienen de asistencias fuera del rango (cruces de medianoche)
        if self.deep_clean:
            ShiftLine = self.env['hr.attendance.shift.line'].sudo()
            old_lines = ShiftLine.search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            old_lines.unlink()
        if not attendances:
            raise UserError(_(
                'No hay asistencias en el rango/criterio indicado.\n\n'
                'Verifique:\n'
                ' - Que las fechas (desde/hasta) cubran el periodo de las asistencias.\n'
                ' - Que los filtros (empleado, departamento) no esten excluyendo registros.'
            ))

        # Auto-asignar grupo a las asistencias que no lo tengan
        no_group = attendances.filtered(lambda a: not a.shift_group_id)
        if self.auto_assign_group and no_group:
            for att in no_group:
                ref_date = (att.check_in or fields.Datetime.now()).date()
                grp = att.employee_id.get_active_shift_group(ref_date) if att.employee_id else False
                if grp:
                    att.shift_group_id = grp.id

        if self.shift_group_ids:
            attendances = attendances.filtered(lambda a: a.shift_group_id in self.shift_group_ids)

        ready = attendances.filtered(lambda a: a.shift_group_id and a.check_in and a.check_out)
        skipped_no_checkout = attendances.filtered(lambda a: not a.check_out)
        skipped_no_group = attendances - ready - skipped_no_checkout

        if not ready:
            raise UserError(_(
                'Se encontraron %d asistencias en el periodo, pero ninguna se pudo procesar:\n'
                ' - Sin grupo de turno asignado: %d (asigne el grupo en la ficha del empleado).\n'
                ' - Sin check-out: %d.'
            ) % (len(attendances), len(skipped_no_group), len(skipped_no_checkout)))

        ready._recompute_shift_lines()

        msg = _('Se procesaron %d asistencias correctamente.') % len(ready)
        if skipped_no_group:
            msg += _('\nOmitidas (sin grupo): %d') % len(skipped_no_group)
        if skipped_no_checkout:
            msg += _('\nOmitidas (sin check-out): %d') % len(skipped_no_checkout)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recalculo completado'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            }
        }
