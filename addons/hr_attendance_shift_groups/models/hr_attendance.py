# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'mail.thread', 'mail.activity.mixin']

    shift_group_id = fields.Many2one(
        'hr.shift.group',
        string='Grupo de Turno',
        compute='_compute_shift_group', store=True, readonly=False,
        tracking=True,
    )
    shift_date = fields.Date(string='Fecha',
        compute='_compute_shift_date', store=True, index=True)
    shift_line_ids = fields.One2many('hr.attendance.shift.line', 'attendance_id',
        string='Distribucion por Franja', copy=False)
    hours_ordinary = fields.Float(string='Horas Ordinarias',
        compute='_compute_hour_totals', store=True, digits=(5, 2))
    hours_extra_day = fields.Float(string='Horas Extra Diurnas',
        compute='_compute_hour_totals', store=True, digits=(5, 2))
    hours_extra_night = fields.Float(string='Horas Extra Nocturnas',
        compute='_compute_hour_totals', store=True, digits=(5, 2))
    hours_break = fields.Float(string='Horas Descanso (no pagadas)',
        compute='_compute_hour_totals', store=True, digits=(5, 2))
    crosses_midnight = fields.Boolean(
        string='Cruza Medianoche',
        compute='_compute_crosses_midnight', store=True,
        help='True si la asistencia abarca dos fechas calendario.',
    )

    manually_corrected = fields.Boolean(
        string='Corregida manualmente', default=False, copy=False, tracking=True,
        help='Se marca cuando un usuario ajusta a mano la entrada/salida. La '
             'descarga y la reconstruccion automatica NO sobrescriben las '
             'marcaciones con este flag.')

    is_incomplete = fields.Boolean(string='Marcacion Incompleta',
        compute='_compute_is_incomplete', store=True, index=True)
    incomplete_reason = fields.Selection([
        ('ok', 'Completa'),
        ('no_checkin', 'Sin check-in'),
        ('no_checkout', 'Sin check-out'),
        ('no_group', 'Sin grupo de turno'),
        ('too_long', 'Sospechosa: > 18h'),
    ], string='Estado', compute='_compute_is_incomplete', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_crosses_midnight(self):
        for att in self:
            if not att.check_in or not att.check_out:
                att.crosses_midnight = False
                continue
            tz = att._get_employee_tz()
            ci = pytz.utc.localize(att.check_in).astimezone(tz)
            co = pytz.utc.localize(att.check_out).astimezone(tz)
            att.crosses_midnight = ci.date() != co.date()

    @api.depends('check_in', 'check_out', 'shift_group_id')
    def _compute_is_incomplete(self):
        for att in self:
            if not att.check_in:
                att.incomplete_reason = 'no_checkin'; att.is_incomplete = True
            elif not att.check_out:
                att.incomplete_reason = 'no_checkout'; att.is_incomplete = True
            elif (att.check_out - att.check_in).total_seconds() > 18 * 3600:
                # Asistencia mayor a 18 horas: probablemente marcacion huerfana
                att.incomplete_reason = 'too_long'; att.is_incomplete = True
            elif not att.shift_group_id:
                att.incomplete_reason = 'no_group'; att.is_incomplete = True
            else:
                att.incomplete_reason = 'ok'; att.is_incomplete = False

    @api.depends('employee_id', 'check_in')
    def _compute_shift_group(self):
        for att in self:
            if not att.employee_id:
                att.shift_group_id = False
                continue
            ref_date = (att.check_in or fields.Datetime.now()).date()
            att.shift_group_id = att.employee_id.get_active_shift_group(ref_date)

    @api.depends('check_in', 'employee_id')
    def _compute_shift_date(self):
        for att in self:
            if not att.check_in:
                att.shift_date = False
                continue
            tz = att._get_employee_tz()
            local_dt = pytz.utc.localize(att.check_in).astimezone(tz)
            att.shift_date = local_dt.date()

    @api.depends('shift_line_ids.hours_worked', 'shift_line_ids.slot_type')
    def _compute_hour_totals(self):
        for att in self:
            ord_h = xd_h = xn_h = br_h = 0.0
            for line in att.shift_line_ids:
                if line.slot_type == 'ordinary': ord_h += line.hours_worked
                elif line.slot_type == 'extra_day': xd_h += line.hours_worked
                elif line.slot_type == 'extra_night': xn_h += line.hours_worked
                elif line.slot_type == 'break': br_h += line.hours_worked
            att.hours_ordinary = ord_h; att.hours_extra_day = xd_h
            att.hours_extra_night = xn_h; att.hours_break = br_h

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_shift_lines()
        return records

    def write(self, vals):
        # Crossnexion: toda edicion MANUAL de entrada/salida marca la
        # marcacion como "corregida a mano" para que la re-descarga /
        # reconstruccion automatica no la sobrescriba. La reconstruccion del
        # modulo biometrico pasa context zk_rebuild=True para no auto-marcarse.
        if (('check_in' in vals or 'check_out' in vals)
                and 'manually_corrected' not in vals
                and not self.env.context.get('zk_rebuild')
                and not self.env.context.get('install_mode')):
            vals = dict(vals, manually_corrected=True)
        track_before = {}
        if 'check_in' in vals or 'check_out' in vals:
            for att in self:
                track_before[att.id] = (att.check_in, att.check_out)
        res = super().write(vals)
        triggers = {'check_in', 'check_out', 'employee_id', 'shift_group_id'}
        if triggers.intersection(vals.keys()):
            self._recompute_shift_lines()
        if track_before:
            for att in self:
                old_in, old_out = track_before.get(att.id, (None, None))
                changes = []
                if 'check_in' in vals and old_in != att.check_in:
                    changes.append(_('Check-in: %s -> %s') % (old_in or '-', att.check_in or '-'))
                if 'check_out' in vals and old_out != att.check_out:
                    changes.append(_('Check-out: %s -> %s') % (old_out or '-', att.check_out or '-'))
                if changes and hasattr(att, 'message_post'):
                    att.message_post(body='<br/>'.join(changes))
        return res

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        # Crossnexion: durante la reconstruccion automatica desde el reloj
        # (context zk_rebuild) se permiten varias marcaciones "abiertas" (sin
        # salida) en dias distintos: son olvidos de marcar salida que el
        # supervisor corrige luego en "Correccion de Marcaciones". La
        # reconstruccion ya garantiza UNA marcacion por dia sin solapamientos,
        # asi que se omite la validacion estandar (que prohibe mas de una
        # marcacion abierta por empleado). Las ediciones MANUALES siguen con la
        # validacion completa de Odoo.
        if self.env.context.get('zk_rebuild'):
            return
        return super()._check_validity()

    def action_recompute_shift_lines(self):
        self._recompute_shift_lines()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Recalculo completado',
                'message': 'Se recalcularon %d asistencias.' % len(self),
                'type': 'success', 'sticky': False},
        }

    def action_complete_missing_checkout(self):
        self.ensure_one()
        if self.check_out:
            raise UserError(_('Esta asistencia ya tiene check-out.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Completar Marcacion'),
            'res_model': 'hr.attendance.fix.wizard',
            'view_mode': 'form', 'target': 'new',
            'context': {'default_attendance_id': self.id},
        }

    def _suggest_checkout_datetime(self, mode='shift_end', fixed_hour=None):
        self.ensure_one()
        if not self.check_in:
            return False
        tz = self._get_employee_tz()
        local_in = pytz.utc.localize(self.check_in).astimezone(tz)
        target_hour = False
        if mode == 'fixed':
            target_hour = fixed_hour
        elif mode == 'shift_end':
            grp = self.shift_group_id
            if grp:
                slots = grp.slot_ids.filtered(
                    lambda s: s.slot_type in ('ordinary', 'extra_day') and not s.crosses_midnight
                )
                if slots:
                    target_slot = max(slots, key=lambda s: s.time_to)
                    target_hour = target_slot.time_to
        elif mode == 'calendar':
            cal = (self.employee_id.resource_calendar_id if self.employee_id else False)
            if cal and cal.attendance_ids:
                weekday = str(local_in.weekday())
                day_atts = cal.attendance_ids.filtered(lambda a: a.dayofweek == weekday)
                if day_atts:
                    target_hour = max(day_atts.mapped('hour_to'))
        if target_hour is None or target_hour is False:
            return False
        h = int(target_hour); m = int(round((target_hour - h) * 60))
        if h >= 24: h, m = 23, 59
        local_out = local_in.replace(hour=h, minute=m, second=0, microsecond=0)
        if local_out <= local_in:
            local_out += timedelta(days=1)
        return local_out.astimezone(pytz.UTC).replace(tzinfo=None)

    def _get_employee_tz(self):
        self.ensure_one()
        tz_name = (
            (self.employee_id.tz if self.employee_id else False)
            or (self.employee_id.resource_calendar_id.tz if self.employee_id and self.employee_id.resource_calendar_id else False)
            or self.env.user.tz or 'UTC'
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    # ------------------------------------------------------------------
    # CALCULO con fecha calendario por linea (FIX cruce medianoche)
    # ------------------------------------------------------------------
    def _recompute_shift_lines(self):
        ShiftLine = self.env['hr.attendance.shift.line'].sudo()
        for att in self:
            att.shift_line_ids.sudo().unlink()
            if not att.check_in or not att.check_out or not att.shift_group_id:
                continue
            # SKIP asistencias > 18h: son marcaciones huerfanas (olvido de check-out
            # que cierra automaticamente con el siguiente check-in del usuario, etc).
            # Estas se marcan como is_incomplete=True con reason='too_long' para que
            # el supervisor las corrija manualmente en "Correccion de Marcaciones".
            duration_hours = (att.check_out - att.check_in).total_seconds() / 3600.0
            if duration_hours > 18.0:
                _logger.info(
                    "Asistencia %s OMITIDA del calculo (duracion %.1fh > 18h - probable marcacion huerfana)",
                    att.id, duration_hours)
                continue
            try:
                lines_data = att._compute_distribution()
            except Exception:
                _logger.exception("Error calculando distribucion de horas para asistencia %s", att.id)
                continue
            for slot, day, hours in lines_data:
                if hours <= 0.0001:
                    continue
                ShiftLine.create({
                    'attendance_id': att.id,
                    'slot_id': slot.id,
                    'date': day,
                    'hours_worked': hours,
                })

    def _compute_distribution(self):
        """Distribuye [check_in, check_out] en franjas, GENERANDO UNA LINEA
        POR (slot, fecha calendario). Una asistencia que cruza medianoche
        produce lineas con fechas distintas (la del check_in y la siguiente).
        Retorna lista de tuplas: (slot, date, hours).
        """
        self.ensure_one()
        tz = self._get_employee_tz()
        check_in_local = pytz.utc.localize(self.check_in).astimezone(tz)
        check_out_local = pytz.utc.localize(self.check_out).astimezone(tz)
        if check_out_local <= check_in_local:
            return []

        # ----- TOLERANCIA DE MARCACION -----
        # Si el check_in cae dentro de [oficial_inicio +/- tol_morning] minutos,
        # se redondea al inicio oficial (sin extras antes ni descuento).
        # Si el check_out cae dentro de [oficial_fin +/- tol_evening] minutos,
        # se redondea al fin oficial (sin extras despues ni descuento).
        # La tolerancia es una ZONA FRANCA: dentro de ella la marcacion se trata
        # como el horario oficial (sin extra ni descuento); si se SUPERA, el
        # extra/descuento se cuenta desde el BORDE de la tolerancia (la gracia
        # nunca se cobra). Se logra "acercando" la marcacion al horario oficial
        # hasta el tope de la tolerancia.
        grp = self.shift_group_id
        tol_morning = (getattr(grp, 'tolerance_morning_minutes', 0) or 0) / 60.0
        tol_evening = (getattr(grp, 'tolerance_evening_minutes', 0) or 0) / 60.0
        if tol_morning or tol_evening:
            try:
                official_start, official_end = grp.get_shift_official_bounds()
            except Exception:
                official_start, official_end = None, None

            # Limite duro: si la desviacion supera 30 min, la tolerancia se
            # PIERDE y el tiempo se cuenta completo desde el horario oficial
            # (extra o descuento). Dentro de 30 min rige la zona franca (se
            # acerca la marcacion al oficial hasta el tope de la tolerancia).
            # Limites separados de ENTRADA y SALIDA (con fallback al legacy).
            try:
                hl_entry_min, hl_exit_min = grp.get_hard_limits_minutes()
            except Exception:
                _leg = (getattr(grp, 'hard_limit_minutes', 30) or 30)
                hl_entry_min = hl_exit_min = _leg
            hl_entry = hl_entry_min / 60.0
            hl_exit = hl_exit_min / 60.0

            def _shift_to_official(dec, official, tol, limit):
                if official is None or not tol:
                    return dec
                if abs(dec - official) > limit:
                    return dec
                if dec > official:
                    return max(official, dec - tol)
                if dec < official:
                    return min(official, dec + tol)
                return dec

            def _set_time(dt_local, dec):
                h = int(dec)
                m = int(round((dec - h) * 60))
                if m >= 60:
                    h += 1
                    m -= 60
                if h >= 24:
                    h, m = 23, 59
                return dt_local.replace(hour=h, minute=m, second=0, microsecond=0)

            if official_start is not None and tol_morning:
                ci_dec = check_in_local.hour + check_in_local.minute / 60.0 + check_in_local.second / 3600.0
                check_in_local = _set_time(
                    check_in_local, _shift_to_official(ci_dec, official_start, tol_morning, hl_entry))
            if official_end is not None and tol_evening:
                co_dec = check_out_local.hour + check_out_local.minute / 60.0 + check_out_local.second / 3600.0
                check_out_local = _set_time(
                    check_out_local, _shift_to_official(co_dec, official_end, tol_evening, hl_exit))
            # Re-validar luego del ajuste
            if check_out_local <= check_in_local:
                return []

        slots = self.shift_group_id.get_ordered_slots()
        # Acumulador: (slot_id, fecha) -> horas
        acc = {}
        slot_by_id = {slot.id: slot for slot in slots}

        cursor = check_in_local
        end = check_out_local
        while cursor < end:
            day_start = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
            next_day = day_start + timedelta(days=1)
            day_end = min(next_day, end)
            wf = (cursor - day_start).total_seconds() / 3600.0
            wt = (day_end - day_start).total_seconds() / 3600.0
            current_date = cursor.date()  # Fecha CALENDARIO de este segmento
            for slot in slots:
                hours = self._intersect_hours(slot, wf, wt)
                if hours > 0:
                    key = (slot.id, current_date)
                    acc[key] = acc.get(key, 0.0) + hours
            cursor = next_day

        # Ordenar por fecha y secuencia del slot
        result = [(slot_by_id[sid], dt, hrs) for (sid, dt), hrs in acc.items()]
        result.sort(key=lambda x: (x[1], x[0].sequence))
        return result

    @staticmethod
    def _intersect_hours(slot, work_from, work_to):
        if work_to <= work_from:
            return 0.0
        total = 0.0
        for seg_from, seg_to in slot.get_segments():
            lo = max(work_from, seg_from); hi = min(work_to, seg_to)
            if hi > lo:
                total += hi - lo
        return total

    # ------------------------------------------------------------------
    # Crossnexion: dividir una marcacion sospechosa cuyo check_in y
    # check_out estan en dias diferentes (probable olvido de marcar).
    # ------------------------------------------------------------------
    def action_split_orphan_checkout(self):
        """Divide la marcacion en dos:
          1. Mantiene el check_in como esta, BORRA el check_out
             (queda como olvido de marcar salida).
          2. Crea una nueva marcacion con check_in = check_out actual,
             check_out = check_out actual (registra solo el punch out
             como entrada huerfana).
        Solo aplicable cuando check_in y check_out estan en dias distintos.
        """
        from odoo.exceptions import UserError
        Att = self.env['hr.attendance']
        for rec in self:
            if not rec.check_in or not rec.check_out:
                raise UserError(_(
                    'La marcacion %s no tiene check_in y check_out completos.'
                ) % rec.display_name)
            if rec.check_in.date() == rec.check_out.date():
                raise UserError(_(
                    'La marcacion %s no cruza dias. Si esta seguro de querer '
                    'dividirla, hagalo manualmente.'
                ) % rec.display_name)

            check_out_orig = rec.check_out
            # Capturar valores actuales para crear la nueva
            new_vals = {
                'employee_id': rec.employee_id.id,
                'check_in': check_out_orig,
                'check_out': check_out_orig,
            }
            # Borrar check_out de la actual
            rec.write({'check_out': False})
            # Crear la huerfana con duracion cero
            Att.create(new_vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marcaciones divididas'),
                'message': _(
                    'Se dividieron %d marcacion(es). Revise: el check_in '
                    'quedo abierto y el check_out se registro como '
                    'evento huerfano (duracion 0).'
                ) % len(self),
                'type': 'success',
                'sticky': True,
            },
        }
