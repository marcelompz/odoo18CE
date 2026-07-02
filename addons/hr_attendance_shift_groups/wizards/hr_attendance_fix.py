# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# ===================================================================
#  Wizard 1-a-1: Completar marcacion faltante
# ===================================================================
class HrAttendanceFixWizard(models.TransientModel):
    _name = 'hr.attendance.fix.wizard'
    _description = 'Wizard: Completar marcacion faltante en una asistencia'

    attendance_id = fields.Many2one('hr.attendance', string='Asistencia', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='attendance_id.employee_id', readonly=True)
    incomplete_reason = fields.Selection(related='attendance_id.incomplete_reason', readonly=True)
    current_check_in = fields.Datetime(related='attendance_id.check_in', readonly=True, string='Check-in actual')
    current_check_out = fields.Datetime(related='attendance_id.check_out', readonly=True, string='Check-out actual')
    new_check_in = fields.Datetime(string='Nuevo check-in')
    new_check_out = fields.Datetime(string='Nuevo check-out')
    note = fields.Char(string='Comentario', help='Razon del ajuste (queda en el log).')

    @api.onchange('attendance_id', 'incomplete_reason')
    def _onchange_suggest(self):
        if not self.attendance_id:
            return
        att = self.attendance_id
        if att.incomplete_reason == 'no_checkout' and att.check_in:
            self.new_check_in = att.check_in
            self.new_check_out = att.check_in + timedelta(hours=8)
        elif att.incomplete_reason == 'no_checkin' and att.check_out:
            self.new_check_in = att.check_out - timedelta(hours=8)
            self.new_check_out = att.check_out

    def action_apply(self):
        self.ensure_one()
        att = self.attendance_id
        vals = {}
        if self.new_check_in:
            vals['check_in'] = self.new_check_in
        if self.new_check_out:
            vals['check_out'] = self.new_check_out
        if not vals:
            raise UserError(_('Indique al menos un valor (check-in o check-out) para corregir.'))
        ci = vals.get('check_in', att.check_in); co = vals.get('check_out', att.check_out)
        if ci and co and ci >= co:
            raise UserError(_('El check-in debe ser anterior al check-out.'))
        att.write(vals)
        msg = _('Marcacion corregida.')
        if self.note:
            msg += '<br/><b>%s:</b> %s' % (_('Motivo'), self.note)
        if 'check_in' in vals:
            msg += '<br/>%s: %s' % (_('Nuevo check-in'), vals['check_in'])
        if 'check_out' in vals:
            msg += '<br/>%s: %s' % (_('Nuevo check-out'), vals['check_out'])
        att.message_post(body=msg)
        return {'type': 'ir.actions.act_window_close'}


# ===================================================================
#  Wizard: Crear asistencia manual
# ===================================================================
class HrAttendanceCreateWizard(models.TransientModel):
    _name = 'hr.attendance.create.wizard'
    _description = 'Wizard: Crear asistencia faltante'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    check_in = fields.Datetime(string='Check-in', required=True, default=fields.Datetime.now)
    check_out = fields.Datetime(string='Check-out')
    note = fields.Char(string='Comentario')

    def action_create(self):
        self.ensure_one()
        if self.check_out and self.check_in >= self.check_out:
            raise UserError(_('El check-in debe ser anterior al check-out.'))
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_id.id,
            'check_in': self.check_in,
            'check_out': self.check_out or False,
            'manually_corrected': True,
        })
        if self.note:
            att.message_post(body=_('Asistencia creada manualmente. Motivo: %s') % self.note)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asistencia creada'),
            'res_model': 'hr.attendance',
            'view_mode': 'form', 'res_id': att.id, 'target': 'current',
        }


# ===================================================================
#  Wizard MASIVO: Asignar grupo de turno
# ===================================================================
class HrAttendanceAssignGroupWizard(models.TransientModel):
    _name = 'hr.attendance.assign.group.wizard'
    _description = 'Wizard: Asignar grupo de turno masivamente'

    attendance_ids = fields.Many2many('hr.attendance', string='Asistencias seleccionadas', required=True)
    shift_group_id = fields.Many2one('hr.shift.group', string='Grupo de Turno', required=True)
    use_employee_group = fields.Boolean(string='Usar grupo del empleado/contrato', default=False,
        help='Si esta activo, se ignora el campo "Grupo de Turno" y se asigna el grupo del empleado/contrato.')
    overwrite_existing = fields.Boolean(string='Sobrescribir las que ya tienen grupo', default=False)
    recompute_lines = fields.Boolean(string='Recalcular distribucion por franja', default=True)
    attendance_count = fields.Integer(string='Cantidad', compute='_compute_count')

    @api.depends('attendance_ids')
    def _compute_count(self):
        for w in self:
            w.attendance_count = len(w.attendance_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids and self.env.context.get('active_model') == 'hr.attendance':
            res['attendance_ids'] = [(6, 0, active_ids)]
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.attendance_ids:
            raise UserError(_('No hay asistencias seleccionadas.'))
        target = self.attendance_ids
        if not self.overwrite_existing:
            target = target.filtered(lambda a: not a.shift_group_id)
        if not target:
            raise UserError(_('No hay asistencias para procesar (todas ya tienen grupo).'))
        updated = 0; skipped = 0
        for att in target:
            if self.use_employee_group:
                if not att.employee_id:
                    skipped += 1; continue
                ref_date = (att.check_in or fields.Datetime.now()).date()
                grp = att.employee_id.get_active_shift_group(ref_date)
                if not grp:
                    skipped += 1; continue
                att.shift_group_id = grp.id
            else:
                att.shift_group_id = self.shift_group_id.id
            updated += 1
        if self.recompute_lines:
            target._recompute_shift_lines()
        msg = _('Se actualizaron %d asistencias.') % updated
        if skipped:
            msg += _('\nOmitidas: %d') % skipped
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Asignacion completada'), 'message': msg,
                       'type': 'success', 'sticky': True}
        }


# ===================================================================
#  Wizard MASIVO: Completar check-out faltante
# ===================================================================
CHECKOUT_MODES = [
    ('shift_end', 'Fin del turno (ultima franja del grupo)'),
    ('calendar', 'Fin de jornada del Horario de Trabajo'),
    ('fixed', 'Hora fija manual'),
]


class HrAttendanceCompleteCheckoutWizard(models.TransientModel):
    _name = 'hr.attendance.complete.checkout.wizard'
    _description = 'Wizard: Completar check-out faltante (masivo)'

    attendance_ids = fields.Many2many('hr.attendance',
        string='Asistencias seleccionadas', required=True)
    mode = fields.Selection(CHECKOUT_MODES, string='Modo', default='shift_end', required=True,
        help='Como calcular la hora de salida que se aplicara a cada asistencia.')
    fixed_hour = fields.Float(string='Hora de salida (fija)', default=17.0,
        help='Solo si modo = Hora fija manual. Formato decimal: 17.5 = 17:30')
    note = fields.Char(string='Motivo del ajuste', required=True,
        help='Razon del ajuste (obligatorio). Quedara en el chatter de cada asistencia.')
    recompute_lines = fields.Boolean(string='Recalcular distribucion por franja', default=True)

    attendance_count = fields.Integer(string='Total seleccionadas', compute='_compute_counts')
    pending_count = fields.Integer(string='Sin check-out (a procesar)', compute='_compute_counts')

    @api.depends('attendance_ids')
    def _compute_counts(self):
        for w in self:
            w.attendance_count = len(w.attendance_ids)
            w.pending_count = len(w.attendance_ids.filtered(lambda a: a.check_in and not a.check_out))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids and self.env.context.get('active_model') == 'hr.attendance':
            res['attendance_ids'] = [(6, 0, active_ids)]
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.note or not self.note.strip():
            raise UserError(_('Debe indicar un motivo para el ajuste.'))
        if self.mode == 'fixed' and (self.fixed_hour is None or self.fixed_hour < 0 or self.fixed_hour >= 24):
            raise UserError(_('La hora fija debe estar entre 0.0 y 23.99 (formato decimal).'))

        targets = self.attendance_ids.filtered(lambda a: a.check_in and not a.check_out)
        if not targets:
            raise UserError(_('Las asistencias seleccionadas no tienen check-out faltante.'))

        ok_count = 0
        skipped = []
        user_name = self.env.user.name or 'sistema'
        now_str = fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S UTC')

        for att in targets:
            checkout_dt = att._suggest_checkout_datetime(
                mode=self.mode,
                fixed_hour=self.fixed_hour if self.mode == 'fixed' else None,
            )
            if not checkout_dt:
                skipped.append((att, _('No se pudo determinar hora de salida')))
                continue
            if checkout_dt <= att.check_in:
                skipped.append((att, _('Hora calculada anterior al check-in')))
                continue
            # Aplicar y postear log de auditoria
            att.write({'check_out': checkout_dt})
            audit = _(
                '<b>Check-out completado masivamente</b><br/>'
                'Hora aplicada: <b>%s</b> (modo: %s)<br/>'
                'Motivo: %s<br/>'
                'Aprobado por: <b>%s</b><br/>'
                'Fecha del ajuste: %s'
            ) % (
                checkout_dt.strftime('%d/%m/%Y %H:%M:%S'),
                dict(CHECKOUT_MODES).get(self.mode, self.mode),
                self.note,
                user_name,
                now_str,
            )
            att.message_post(body=audit)
            ok_count += 1

        if self.recompute_lines and ok_count:
            targets.filtered(lambda a: a.check_out)._recompute_shift_lines()

        msg = _('Se completaron %d check-out.') % ok_count
        if skipped:
            msg += _('\nOmitidas: %d') % len(skipped)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Check-out completado'), 'message': msg,
                'type': 'success', 'sticky': True,
            }
        }


# ===================================================================
#  Wizard: Regenerar Tablero Diario (planilla por grupo)
# ===================================================================
class HrAttendanceDailyRegenWizard(models.TransientModel):
    _name = 'hr.attendance.daily.regen.wizard'
    _description = 'Wizard: Regenerar Tablero Diario'

    date_from = fields.Date(string='Fecha desde', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='Fecha hasta', required=True,
        default=lambda self: _last_day_of_month(fields.Date.context_today(self)))
    employee_ids = fields.Many2many('hr.employee', string='Empleados (vacio = todos)')
    shift_group_ids = fields.Many2many('hr.shift.group', string='Grupos (vacio = todos)')

    def action_regenerate(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "desde" debe ser anterior a "hasta".'))
        n = self.env['hr.attendance.daily.report'].regenerate(
            date_from=self.date_from,
            date_to=self.date_to,
            employee_ids=self.employee_ids.ids if self.employee_ids else None,
            shift_group_ids=self.shift_group_ids.ids if self.shift_group_ids else None,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tablero regenerado'),
                'message': _('Se generaron %d filas en el tablero diario.') % n,
                'type': 'success', 'sticky': False,
            }
        }


def _last_day_of_month(d):
    if d.month == 12:
        return d.replace(day=31)
    nxt = d.replace(month=d.month + 1, day=1)
    return nxt - timedelta(days=1)
