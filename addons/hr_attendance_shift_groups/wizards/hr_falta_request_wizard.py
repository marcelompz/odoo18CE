# -*- coding: utf-8 -*-
"""Wizard para solicitar justificacion de faltas reutilizando hr.leave."""
from datetime import datetime, time
from odoo import _, api, fields, models
from odoo.exceptions import UserError


REASON_TYPE_MAP = {
    'olvido': ('Olvido de Marcacion', True),
    'enfermedad': ('Tiempo personal por enfermedad', True),
    'vacaciones': ('Vacaciones', True),
    'otros': ('Permiso Especial', True),
}


class HrFaltaRequestWizard(models.TransientModel):
    _name = 'hr.falta.request.wizard'
    _description = 'Wizard Solicitar Aprobacion de Faltas (via hr.leave)'

    employee_id = fields.Many2one('hr.employee', string='Empleado',
                                  required=True)
    daily_report_ids = fields.Many2many(
        'hr.attendance.daily.report',
        string='Dias seleccionados (FALTA)', required=True,
    )
    reason = fields.Selection([
        ('olvido', 'Olvido de marcacion'),
        ('enfermedad', 'Ausencia por enfermedad'),
        ('vacaciones', 'Vacaciones / Permiso'),
        ('otros', 'Otros motivos'),
    ], string='Motivo', required=True)
    holiday_status_id = fields.Many2one(
        'hr.leave.type', string='Tipo de Tiempo Personal',
        compute='_compute_holiday_status_id', store=False, readonly=False,
    )
    description = fields.Text(string='Descripcion / Detalle')
    summary_html = fields.Html(string='Resumen', compute='_compute_summary',
                               readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ids = self.env.context.get('active_ids') or []
        if ids:
            Report = self.env['hr.attendance.daily.report']
            rows = Report.browse(ids)
            faltas = rows.filtered(lambda r: r.absence_status == 'absence')
            if not faltas:
                raise UserError(_('No hay dias con estado FALTA en la seleccion.'))
            employees = faltas.mapped('employee_id')
            if len(employees) > 1:
                raise UserError(_('Seleccione FALTAS de un solo empleado.'))
            res['employee_id'] = employees[0].id
            res['daily_report_ids'] = [(6, 0, faltas.ids)]
        return res

    @api.depends('reason')
    def _compute_holiday_status_id(self):
        LeaveType = self.env['hr.leave.type'].sudo()
        for w in self:
            if not w.reason:
                w.holiday_status_id = False
                continue
            type_name, _is_rem = REASON_TYPE_MAP.get(w.reason, (None, True))
            if not type_name:
                w.holiday_status_id = False
                continue
            lt = LeaveType.search([('name', '=', type_name)], limit=1)
            if not lt:
                lt = LeaveType.search([('name', 'ilike', type_name)], limit=1)
            w.holiday_status_id = lt.id if lt else False

    @api.depends('daily_report_ids', 'employee_id')
    def _compute_summary(self):
        for w in self:
            if not w.daily_report_ids:
                w.summary_html = '<p>No hay dias seleccionados.</p>'
                continue
            html = '<p><b>Empleado:</b> %s</p>' % (w.employee_id.name or '')
            html += '<p><b>Dias:</b> %d</p>' % len(w.daily_report_ids)
            html += '<ul>'
            for r in w.daily_report_ids.sorted('date'):
                html += '<li>%s</li>' % r.date
            html += '</ul>'
            w.summary_html = html

    def _ensure_leave_type(self, name, is_remunerated=True):
        """Busca o crea hr.leave.type. Odoo 18: requires_allocation Selection."""
        LeaveType = self.env['hr.leave.type'].sudo()
        lt = LeaveType.search([('name', '=', name)], limit=1)
        if lt:
            return lt
        vals = {
            'name': name,
            'requires_allocation': 'no',
            'leave_validation_type': 'manager',
            'allocation_validation_type': 'no_validation',
            'time_type': 'leave',
            'request_unit': 'day',
        }
        if 'is_remunerated_default' in LeaveType._fields:
            vals['is_remunerated_default'] = is_remunerated
        try:
            lt = LeaveType.create(vals)
        except Exception:
            try:
                self.env.cr.rollback()
            except Exception:
                pass
            lt = LeaveType.with_context(active_test=False).search([], limit=1)
        return lt

    def _date_ranges(self, dates):
        if not dates:
            return []
        sorted_dates = sorted(set(dates))
        ranges = []
        start = prev = sorted_dates[0]
        for d in sorted_dates[1:]:
            if (d - prev).days == 1:
                prev = d
            else:
                ranges.append((start, prev))
                start = prev = d
        ranges.append((start, prev))
        return ranges

    def action_create_request(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_('Seleccione un motivo.'))
        type_name, is_rem = REASON_TYPE_MAP.get(self.reason, (None, True))
        leave_type = self.holiday_status_id
        if not leave_type:
            leave_type = self._ensure_leave_type(type_name, is_rem)
        if not leave_type:
            raise UserError(_('No se pudo resolver un Tipo de Tiempo Personal. '
                              'Configurelo en Tiempo Personal > Configuracion.'))
        Leave = self.env['hr.leave'].sudo()
        dates = self.daily_report_ids.mapped('date')
        ranges = self._date_ranges(dates)
        leaves_created = self.env['hr.leave']
        reason_label = dict(self._fields['reason'].selection).get(
            self.reason, self.reason)
        for date_from, date_to in ranges:
            df = datetime.combine(date_from, time(0, 0))
            dt = datetime.combine(date_to, time(23, 59))
            vals = {
                'employee_id': self.employee_id.id,
                'holiday_status_id': leave_type.id,
                'date_from': df,
                'date_to': dt,
                'request_date_from': date_from,
                'request_date_to': date_to,
                'name': '[FALTA->Solicitud] %s (Motivo: %s)' % (
                    self.description or '', reason_label),
            }
            if 'is_remunerated' in Leave._fields:
                vals['is_remunerated'] = is_rem
            leave = Leave.create(vals)
            try:
                leave.action_confirm()
            except Exception:
                leave.write({'state': 'confirm'})
            leaves_created |= leave
            ds = [d for d in dates if date_from <= d <= date_to]
            rows = self.daily_report_ids.filtered(lambda r: r.date in ds)
            rows.write({'request_state': 'pending'})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitudes creadas (%d)') % len(leaves_created),
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
            'domain': [('id', 'in', leaves_created.ids)],
            'target': 'current',
        }
