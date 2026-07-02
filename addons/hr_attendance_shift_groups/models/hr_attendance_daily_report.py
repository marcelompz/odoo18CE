# -*- coding: utf-8 -*-
"""Modelo agregador: una fila por (empleado, dia) con horas pre-calculadas
por cada franja de los grupos Operativo y Administrativo. Incluye
exportacion a Excel replicando el formato de la planilla modelo y
deteccion de FALTAS / vacaciones / licencias / fines de semana / feriados.
"""
import base64
import io
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


# ----------------------------------------------------------------------
# Crossnexion: utilidades de intervalos (en horas decimales del dia) para
# calcular "a Descontar" por rangos sobre las franjas ordinarias del turno.
# ----------------------------------------------------------------------
def _iv_subtract(intervals, cuts):
    """Resta a cada intervalo los 'cuts' (listas de (inicio, fin))."""
    result = []
    for (s, e) in intervals:
        pieces = [(s, e)]
        for (cs, ce) in cuts:
            nxt = []
            for (ps, pe) in pieces:
                if ce <= ps or cs >= pe:
                    nxt.append((ps, pe))
                else:
                    if cs > ps:
                        nxt.append((ps, cs))
                    if ce < pe:
                        nxt.append((ce, pe))
            pieces = nxt
        result.extend(pieces)
    return result


def _iv_intersect(a, b):
    out = []
    for (s, e) in a:
        for (os, oe) in b:
            lo = max(s, os)
            hi = min(e, oe)
            if hi > lo:
                out.append((lo, hi))
    return out


def _iv_measure(intervals):
    return sum(max(0.0, e - s) for (s, e) in intervals)


class HrAttendanceDailyReport(models.Model):
    _name = 'hr.attendance.daily.report'
    _description = 'Tablero Diario por Empleado (planilla)'
    _order = 'date desc, employee_id'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Colaborador',
        required=True, ondelete='cascade', index=True)
    department_id = fields.Many2one(related='employee_id.department_id',
        string='Departamento', store=True, index=True)
    date = fields.Date(string='Dia', required=True, index=True)
    shift_group_id = fields.Many2one('hr.shift.group', string='Grupo de Turno',
        required=True, index=True, ondelete='cascade')
    shift_group_code = fields.Char(related='shift_group_id.code', store=True, string='Codigo Grupo')
    company_id = fields.Many2one('res.company', related='employee_id.company_id',
        store=True, index=True)
    has_attendance = fields.Boolean(string='Tiene marcacion', default=False)
    is_missing = fields.Boolean(string='Sin marcacion', default=True,
        help='Dia sin asistencia registrada (se muestra en rojo).')

    absence_status = fields.Selection([
        ('present', 'Presente'),
        ('leave', 'Ausencia justificada'),
        ('rest', 'Descanso/Feriado'),
        ('absence', 'Falta'),
    ], string='Estado del dia', default='absence', index=True)
    leave_id = fields.Many2one('hr.leave', string='Permiso/Vacacion')
    leave_type_name = fields.Char(string='Tipo de Ausencia')

    justification_id = fields.Many2one('hr.falta.justification',
        string='Solicitud de Justificacion', readonly=True)
    request_state = fields.Selection([
        ('pending', 'Pendiente aprobacion'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ], string='Estado solicitud', readonly=True)

    h_oper_extra_dawn  = fields.Float(string='Extra Diurna 06:00-06:30',  digits=(5, 4))
    h_oper_entry       = fields.Float(string='Entrada 06:30-07:30',       digits=(5, 4))
    h_oper_breakfast   = fields.Float(string='Desayuno 07:30-08:10',      digits=(5, 4))
    h_oper_morning     = fields.Float(string='T. Diurno 08:10-11:40',     digits=(5, 4))
    h_oper_lunch       = fields.Float(string='Almuerzo 11:40-13:00',      digits=(5, 4))
    h_oper_afternoon   = fields.Float(string='T. Tarde 13:00-17:00',      digits=(5, 4))
    h_oper_extra_eve   = fields.Float(string='Extra Diurno 17:01-19:59',  digits=(5, 4))
    h_oper_extra_night = fields.Float(string='Extra Nocturno 20:00-05:59', digits=(5, 4))

    h_admin_extra_dawn  = fields.Float(string='Extra Diurna 06:00-07:00', digits=(5, 4))
    h_admin_morning     = fields.Float(string='T. Diurno 07:00-12:00',    digits=(5, 4))
    h_admin_lunch       = fields.Float(string='Almuerzo 12:00-13:00',     digits=(5, 4))
    h_admin_afternoon   = fields.Float(string='T. Tarde 13:00-17:00',     digits=(5, 4))
    h_admin_extra_eve   = fields.Float(string='Extra Diurno 17:01-19:59', digits=(5, 4))
    h_admin_extra_night = fields.Float(string='Extra Nocturno 20:00-05:59', digits=(5, 4))

    total_ordinary    = fields.Float(string='Total Jornada',         digits=(5, 4))
    total_extra_day   = fields.Float(string='Total Extra Diurno',   digits=(5, 4))
    total_extra_night = fields.Float(string='Total Extra Nocturno', digits=(5, 4))
    total_break       = fields.Float(string='Total Descanso',       digits=(5, 4))
    expected_ordinary = fields.Float(string='Jornada Estandar',     digits=(5, 4),
        help='Horas ordinarias que deberia trabajar ese dia segun las franjas '
             'del turno (0 en dias de descanso/feriado).')
    to_deduct         = fields.Float(string='Hs a Descontar',       digits=(5, 4),
        help='Horas a descontar: tardanza, salida temprana y ausencias a mitad '
             'de dia (jornada estandar - ordinarias reales, ya con tolerancia); '
             'dia completo si es FALTA o licencia no remunerada. Un dia con '
             'marcacion incompleta (sin salida) NO descuenta hasta corregirse.')
    has_incomplete_marking = fields.Boolean(string='Marcacion incompleta',
        help='El dia tiene una marcacion sin salida (olvido de marcar). No se '
             'descuenta; corregir en "Correccion de Marcaciones".')
    tolerance_applied = fields.Float(string='Tolerancia aplicada', digits=(5, 4),
        help='Gracia de tolerancia absorbida ese dia (entrada + salida), es '
             'decir los minutos de diferencia con el horario oficial que NO se '
             'pagaron como extra ni se descontaron. Para monitoreo.')
    observation = fields.Char(string='Observacion',
        help='Motivo del descuento/ausencia del dia (permiso, tardanza, salida '
             'temprana, falta, marcacion incompleta).')

    def fmt_hhmm(self, value):
        """Float horas -> 'H:MM' (para los reportes QWeb)."""
        m = int(round((value or 0.0) * 60))
        return "%d:%02d" % (m // 60, m % 60)

    def _emp_tz(self, employee):
        name = (
            (employee.tz if employee else False)
            or (employee.resource_calendar_id.tz
                if employee and employee.resource_calendar_id else False)
            or self.env.user.tz or 'America/Asuncion')
        try:
            return pytz.timezone(name)
        except Exception:
            return pytz.timezone('America/Asuncion')

    def _compute_day_deduction(self, employee, group, day, atts,
                               rem_leaves, norem_leaves):
        """Horas a descontar del dia, por rangos sobre las franjas ORDINARIAS
        (los descansos NO entran). Por cada franja ordinaria se descuenta:
        lo NO cubierto por (presencia + permiso remunerado), MAS lo que cae en
        un permiso NO remunerado. Asi: tardanza/salida temprana/ausencia sin
        permiso -> descuenta; permiso remunerado -> excusa (no descuenta);
        permiso no remunerado -> descuenta sus horas ordinarias; huecos a mitad
        de dia sin permiso -> NO descuentan (corren directo)."""
        tz = self._emp_tz(employee)
        day_start_local = tz.localize(datetime.combine(day, time.min))

        def to_dec(dt_utc):
            loc = pytz.utc.localize(dt_utc).astimezone(tz)
            return (loc - day_start_local).total_seconds() / 3600.0

        def clamp(dt_from, dt_to):
            if not dt_from or not dt_to:
                return None
            a = max(0.0, min(24.0, to_dec(dt_from)))
            b = max(0.0, min(24.0, to_dec(dt_to)))
            return (a, b) if b > a else None

        ord_ranges = [(s.time_from, s.time_to) for s in group.slot_ids
                      if s.slot_type == 'ordinary' and not s.crosses_midnight]
        pres = [r for r in (clamp(a.check_in, a.check_out) for a in atts) if r]

        # TOLERANCIA de entrada/salida: si el primer fichaje cae dentro de la
        # tolerancia del inicio oficial, o el ultimo dentro de la tolerancia del
        # fin oficial, se redondea al horario oficial -> NO genera descuento
        # (igual que en el calculo de horas ordinarias).
        try:
            official_start, official_end = group.get_shift_official_bounds()
        except Exception:
            official_start, official_end = None, None
        tol_m = (getattr(group, 'tolerance_morning_minutes', 0) or 0) / 60.0
        tol_e = (getattr(group, 'tolerance_evening_minutes', 0) or 0) / 60.0

        try:
            _hl_e_min, _hl_x_min = group.get_hard_limits_minutes()
        except Exception:
            _leg = (getattr(group, 'hard_limit_minutes', 30) or 30)
            _hl_e_min = _hl_x_min = _leg
        hard_limit_entry = _hl_e_min / 60.0
        hard_limit_exit = _hl_x_min / 60.0

        def _shift(dec, official, tol, limit):
            # Zona franca dentro del limite: acerca la marcacion al horario
            # oficial hasta el tope de la tolerancia. Si la desviacion supera el
            # limite duro, la tolerancia se PIERDE y se cuenta completo desde el
            # oficial.
            if official is None or not tol:
                return dec
            if abs(dec - official) > limit:
                return dec
            if dec > official:
                return max(official, dec - tol)
            if dec < official:
                return min(official, dec + tol)
            return dec

        pres = [(_shift(a, official_start, tol_m, hard_limit_entry),
                 _shift(b, official_end, tol_e, hard_limit_exit))
                for (a, b) in pres]
        rem = [r for r in (clamp(l.date_from, l.date_to) for l in rem_leaves) if r]
        norem = [r for r in (clamp(l.date_from, l.date_to) for l in norem_leaves) if r]

        total = 0.0
        for slot in ord_ranges:
            not_covered = _iv_subtract([slot], pres + rem)
            in_norem = _iv_intersect([slot], norem)
            total += (_iv_measure(not_covered) + _iv_measure(in_norem)
                      - _iv_measure(_iv_intersect(not_covered, in_norem)))
        return total

    def action_view_attendances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Marcaciones de %s - %s') % (self.employee_id.name, self.date),
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('shift_date', '=', self.date),
            ],
            'context': {'default_employee_id': self.employee_id.id},
        }

    def action_export_xlsx_oper(self):
        return self._export_dashboard_xlsx('OPER')

    def action_export_xlsx_admin(self):
        return self._export_dashboard_xlsx('ADMIN')

    def _export_dashboard_xlsx(self, group_code):
        if xlsxwriter is None:
            raise UserError(_('La libreria Python "xlsxwriter" no esta instalada.'))
        recs = self
        if not recs:
            recs = self.search([('shift_group_id.code', '=', group_code)])
        recs = recs.filtered(lambda r: r.shift_group_id.code == group_code)
        if not recs:
            raise UserError(_('No hay datos del grupo %s para exportar.') % group_code)
        buffer = io.BytesIO()
        wb = xlsxwriter.Workbook(buffer, {'in_memory': True})
        self._build_dashboard_sheet(wb, recs, group_code)
        wb.close()
        buffer.seek(0)
        content = buffer.read()
        buffer.close()
        company = (self.env.company.name or 'Empresa').replace(' ', '_')
        date_min = min(recs.mapped('date'))
        date_max = max(recs.mapped('date'))
        file_name = "Planilla_%s_%s_%s_%s.xlsx" % (group_code, company, date_min, date_max)
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'res_model': self._name,
            'res_id': 0,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }

    def _build_dashboard_sheet(self, workbook, recs, group_code):
        if group_code == 'OPER':
            sheet_name = 'Operativo'
            slot_cols = [
                ('Extra Diurna',       '06:00-06:30',  'h_oper_extra_dawn',  'extra'),
                ('Entrada',            '06:30-07:30',  'h_oper_entry',       'ord'),
                ('Desayuno',           '07:30-08:10',  'h_oper_breakfast',   'break'),
                ('Trabajo Diurno',     '08:10-11:40',  'h_oper_morning',     'ord'),
                ('Almuerzo',           '11:40-13:00',  'h_oper_lunch',       'break'),
                ('Trabajo Tarde',      '13:00-17:00',  'h_oper_afternoon',   'ord'),
                ('Extra Diurno',       '17:01-19:59',  'h_oper_extra_eve',   'extra'),
                ('Extra Nocturna',     '20:00-05:59',  'h_oper_extra_night', 'extra_night'),
            ]
        else:
            sheet_name = 'Administrativo'
            slot_cols = [
                ('Extra Diurna',       '06:00-07:00',  'h_admin_extra_dawn',  'extra'),
                ('Trabajo Diurno',     '07:00-12:00',  'h_admin_morning',     'ord'),
                ('Almuerzo',           '12:00-13:00',  'h_admin_lunch',       'break'),
                ('Trabajo Tarde',      '13:00-17:00',  'h_admin_afternoon',   'ord'),
                ('Extra Diurno',       '17:01-19:59',  'h_admin_extra_eve',   'extra'),
                ('Extra Nocturna',     '20:00-05:59',  'h_admin_extra_night', 'extra_night'),
            ]
        ws = workbook.add_worksheet(sheet_name)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial'})
        info_fmt = workbook.add_format({'italic': True, 'font_size': 10, 'font_name': 'Arial', 'align': 'left'})
        hdr_top = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#D9E1F2', 'font_name': 'Arial'})
        hdr_bot = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#B4C6E7', 'font_name': 'Arial', 'text_wrap': True})
        text_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_name': 'Arial'})
        text_red = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_name': 'Arial', 'bg_color': '#F4CCCC'})
        text_yellow = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_name': 'Arial', 'bg_color': '#FFE699'})
        text_blue = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_name': 'Arial', 'bg_color': '#D9E1F2'})
        date_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'dd-mm-yyyy', 'font_name': 'Arial'})
        date_red = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'dd-mm-yyyy', 'font_name': 'Arial', 'bg_color': '#F4CCCC'})
        date_yellow = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'dd-mm-yyyy', 'font_name': 'Arial', 'bg_color': '#FFE699'})
        date_blue = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'dd-mm-yyyy', 'font_name': 'Arial', 'bg_color': '#D9E1F2'})
        time_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'h:mm', 'font_name': 'Arial'})
        time_extra = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#92D050'})
        time_break = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#FFD966'})
        time_red = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#F4CCCC'})
        time_yellow = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#FFE699'})
        time_blue = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#D9E1F2'})
        total_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '[h]:mm', 'font_name': 'Arial', 'bg_color': '#F2F2F2'})
        total_lbl = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_name': 'Arial', 'bg_color': '#F2F2F2'})
        company = self.env.company.name or ''
        date_min = min(recs.mapped('date'))
        date_max = max(recs.mapped('date'))
        n_slot = len(slot_cols)
        total_cols = 2 + 1 + n_slot + 5
        ws.merge_range(0, 0, 0, total_cols - 1, "%s - Tablero %s (%s a %s)" % (company, sheet_name, date_min, date_max), title_fmt)
        ws.merge_range(1, 0, 1, total_cols - 1, "Filas en rojo = FALTA. Amarillo = vacaciones/licencia. Azul = descanso/feriado. Verde = horas extra.", info_fmt)
        ws.set_row(0, 22); ws.set_row(1, 16)
        hdr_row1, hdr_row2 = 2, 3
        ws.merge_range(hdr_row1, 0, hdr_row2, 0, 'Colaborador', hdr_bot)
        ws.merge_range(hdr_row1, 1, hdr_row2, 1, 'Dia', hdr_bot)
        col = 2
        ws.merge_range(hdr_row1, col, hdr_row2, col, 'Estado', hdr_bot); col_status = col; col += 1
        for name, rng, _f, _t in slot_cols:
            ws.write(hdr_row1, col, name, hdr_top)
            ws.write(hdr_row2, col, rng, hdr_bot)
            col += 1
        ws.merge_range(hdr_row1, col, hdr_row2, col, 'Total Jornada', hdr_bot); col_d = col; col += 1
        ws.merge_range(hdr_row1, col, hdr_row2, col, 'Total Extra Diurno', hdr_bot); col_xd = col; col += 1
        ws.merge_range(hdr_row1, col, hdr_row2, col, 'Total Extra Nocturno', hdr_bot); col_xn = col; col += 1
        ws.merge_range(hdr_row1, col, hdr_row2, col, 'Jornada Estandar', hdr_bot); col_exp = col; col += 1
        ws.merge_range(hdr_row1, col, hdr_row2, col, 'a Descontar', hdr_bot); col_ded = col
        ws.set_column(0, 0, 28); ws.set_column(1, 1, 12)
        ws.set_column(col_status, col_status, 24)
        for c in range(col_status + 1, col_status + 1 + n_slot):
            ws.set_column(c, c, 14)
        ws.set_column(col_d, col_ded, 16)
        ws.set_row(hdr_row1, 22); ws.set_row(hdr_row2, 26)
        slot_base = col_status + 1
        ord_cols = [slot_base + i for i, (_, _, _, t) in enumerate(slot_cols) if t == 'ord']
        xd_cols  = [slot_base + i for i, (_, _, _, t) in enumerate(slot_cols) if t == 'extra']
        xn_cols  = [slot_base + i for i, (_, _, _, t) in enumerate(slot_cols) if t == 'extra_night']
        ordered = recs.sorted(lambda r: (r.employee_id.name or '', r.date))
        first_data = hdr_row2 + 1
        current = first_data
        for rec in ordered:
            status = rec.absence_status or ('present' if not rec.is_missing else 'absence')
            if status == 'absence':
                tfmt = text_red; dfmt = date_red; row_time = time_red
                status_label = rec.leave_type_name or 'FALTA'
            elif status == 'leave':
                tfmt = text_yellow; dfmt = date_yellow; row_time = time_yellow
                status_label = rec.leave_type_name or 'Permiso'
            elif status == 'rest':
                tfmt = text_blue; dfmt = date_blue; row_time = time_blue
                status_label = rec.leave_type_name or 'Descanso'
            else:
                tfmt = text_fmt; dfmt = date_fmt; row_time = None
                status_label = 'Presente'
            ws.write(current, 0, rec.employee_id.name or '', tfmt)
            ws.write_datetime(current, 1, fields.Datetime.to_datetime(rec.date), dfmt)
            ws.write(current, col_status, status_label, tfmt)
            for idx, (_, _, field_name, slot_type) in enumerate(slot_cols):
                c = slot_base + idx
                hours = getattr(rec, field_name, 0.0) or 0.0
                if status in ('absence', 'leave', 'rest'):
                    fmt = row_time
                elif slot_type == 'extra' or slot_type == 'extra_night':
                    fmt = time_extra
                elif slot_type == 'break':
                    fmt = time_break
                else:
                    fmt = time_fmt
                ws.write_number(current, c, hours / 24.0, fmt)
            ws.write_formula(current, col_d, self._sum_formula(current, ord_cols), total_fmt, 0.0)
            ws.write_formula(current, col_xd, self._sum_formula(current, xd_cols), total_fmt, 0.0)
            ws.write_formula(current, col_xn, self._sum_formula(current, xn_cols), total_fmt, 0.0)
            ws.write_number(current, col_exp, (rec.expected_ordinary or 0.0) / 24.0, total_fmt)
            ws.write_number(current, col_ded, (rec.to_deduct or 0.0) / 24.0, total_fmt)
            current += 1
        last_data = current - 1
        if last_data >= first_data:
            ws.merge_range(current, 0, current, col_status, 'TOTAL', total_lbl)
            for c in range(slot_base, col_ded + 1):
                col_letter = xlsxwriter.utility.xl_col_to_name(c)
                formula = '=SUM(%s%d:%s%d)' % (col_letter, first_data + 1, col_letter, last_data + 1)
                ws.write_formula(current, c, formula, total_fmt, 0.0)
            ws.set_row(current, 22)
        ws.freeze_panes(hdr_row2 + 1, 2)

    @staticmethod
    def _sum_formula(row, cols):
        if not cols:
            return '=0'
        parts = ['%s%d' % (xlsxwriter.utility.xl_col_to_name(c), row + 1) for c in cols]
        return '=' + '+'.join(parts)

    @api.model
    def _is_global_holiday(self, day, calendar):
        if not calendar:
            return False, None
        day_start = datetime.combine(day, time.min)
        day_end = datetime.combine(day, time.max)
        leave = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', calendar.id),
            ('resource_id', '=', False),
            ('date_from', '<=', day_end),
            ('date_to', '>=', day_start),
        ], limit=1)
        if leave:
            return True, leave.name or _('Feriado')
        return False, None

    @api.model
    def _is_working_day(self, day, calendar):
        if not calendar:
            return True
        weekday = day.weekday()
        atts = calendar.attendance_ids.filtered(
            lambda a: int(a.dayofweek) == weekday and (
                not a.date_from or a.date_from <= day) and (
                not a.date_to or a.date_to >= day)
        )
        return bool(atts)

    def action_request_falta_approval(self):
        """Abre el wizard de solicitud de aprobacion de faltas."""
        if not self:
            raise UserError(_('Seleccione al menos una fila con FALTA.'))
        faltas = self.filtered(lambda r: r.absence_status == 'absence')
        if not faltas:
            raise UserError(_('Seleccione filas con estado "Falta" (rojas).'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitar Aprobacion de Faltas'),
            'res_model': 'hr.falta.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': faltas.ids,
                'active_model': 'hr.attendance.daily.report',
            },
        }

    @api.model
    def regenerate(self, date_from=None, date_to=None, employee_ids=None, shift_group_ids=None):
        if not date_from:
            today = fields.Date.context_today(self)
            date_from = today.replace(day=1)
        if not date_to:
            today = fields.Date.context_today(self)
            if today.month == 12:
                date_to = today.replace(day=31)
            else:
                nxt = today.replace(month=today.month + 1, day=1)
                date_to = nxt - timedelta(days=1)
        all_emps = self.env['hr.employee'].search([])
        if employee_ids:
            all_emps = all_emps.filtered(lambda e: e.id in employee_ids)
        old_domain = [('date', '>=', date_from), ('date', '<=', date_to)]
        if employee_ids:
            old_domain.append(('employee_id', 'in', employee_ids))
        self.search(old_domain).unlink()
        date_list = []
        d = date_from
        while d <= date_to:
            date_list.append(d)
            d += timedelta(days=1)
        rows_to_create = []
        Attendance = self.env['hr.attendance']
        for emp in all_emps:
            for day in date_list:
                grp = emp.get_active_shift_group(day)
                if not grp:
                    continue
                if shift_group_ids and grp.id not in shift_group_ids:
                    continue
                vals = self._build_row_for(emp, day, grp, Attendance)
                if vals:
                    rows_to_create.append(vals)
        if rows_to_create:
            self.create(rows_to_create)
        return len(rows_to_create)

    def _build_row_for(self, employee, day, group, AttendanceModel):
        ShiftLine = self.env['hr.attendance.shift.line']
        lines = ShiftLine.search([('employee_id', '=', employee.id), ('date', '=', day)])
        atts = AttendanceModel.search([('employee_id', '=', employee.id), ('shift_date', '=', day)])
        has_lines = bool(lines)
        slot_totals = {}
        for line in lines:
            slot_totals[line.slot_id.id] = slot_totals.get(line.slot_id.id, 0.0) + line.hours_worked
        oper_map = {
            'Extra Diurno (madrugada)': 'h_oper_extra_dawn',
            'Entrada Diurna':           'h_oper_entry',
            'Desayuno':                 'h_oper_breakfast',
            'Trabajo Diurno':           'h_oper_morning',
            'Almuerzo':                 'h_oper_lunch',
            'Trabajo Tarde':            'h_oper_afternoon',
            'Extra Diurno (tarde)':     'h_oper_extra_eve',
            'Extra Nocturno':           'h_oper_extra_night',
        }
        admin_map = {
            'Extra Diurno (madrugada)': 'h_admin_extra_dawn',
            'Trabajo Diurno':           'h_admin_morning',
            'Almuerzo':                 'h_admin_lunch',
            'Trabajo Tarde':            'h_admin_afternoon',
            'Extra Diurno (tarde)':     'h_admin_extra_eve',
            'Extra Nocturno':           'h_admin_extra_night',
        }
        is_oper = (group.code == 'OPER') or (group.name == 'Operativo')
        slot_map = oper_map if is_oper else admin_map
        had_marking = bool(atts) or has_lines
        leave_rec = False
        leave_label = False
        Leave = self.env['hr.leave']
        day_start = fields.Datetime.to_datetime(day)
        day_end = day_start.replace(hour=23, minute=59, second=59)
        leaves = Leave.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', day_end),
            ('date_to', '>=', day_start),
        ])

        def _is_partial(l):
            # Permiso por horas o medio dia -> parcial (no toma el dia entero).
            return bool(getattr(l, 'request_unit_hours', False)
                        or getattr(l, 'request_unit_half', False))

        def _is_rem(l):
            return bool(l.is_remunerated) if 'is_remunerated' in l._fields else True

        full_leaves = leaves.filtered(lambda l: not _is_partial(l))
        partial_leaves = leaves - full_leaves
        # Permisos parciales (por horas) separados por remunerado/no, para el
        # calculo de "a Descontar" por rangos.
        rem_partial = partial_leaves.filtered(_is_rem)
        norem_partial = partial_leaves - rem_partial

        if full_leaves:
            leave_rec = full_leaves[0]
            base_name = leave_rec.holiday_status_id.name or _('Permiso')
            is_rem = _is_rem(leave_rec)
            leave_label = base_name + (_(' (Remunerada)') if is_rem else _(' (No Remunerada)'))
            #   - Remunerada -> 'leave' (dia pagado, no descuenta)
            #   - No Remunerada -> 'absence' (descuento del dia)
            absence_status = 'leave' if is_rem else 'absence'
        elif had_marking:
            absence_status = 'present'
            if partial_leaves:
                pl = partial_leaves[0]
                leave_rec = pl
                rem_txt = _(' (Remunerado)') if _is_rem(pl) else _(' (No Remunerado)')
                leave_label = (pl.holiday_status_id.name or _('Permiso')) + rem_txt + _(' (parcial)')
        else:
            calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
            is_holiday, holiday_name = self._is_global_holiday(day, calendar)
            if is_holiday:
                leave_label = holiday_name or _('Feriado')
                absence_status = 'rest'
            elif not self._is_working_day(day, calendar):
                weekday_names = [_('Lunes'), _('Martes'), _('Miercoles'), _('Jueves'), _('Viernes'), _('Sabado'), _('Domingo')]
                leave_label = weekday_names[day.weekday()] + ' (Descanso)'
                absence_status = 'rest'
            else:
                leave_label = _('FALTA')
                absence_status = 'absence'
        vals = {
            'employee_id': employee.id,
            'date': day,
            'shift_group_id': group.id,
            'has_attendance': had_marking,
            'is_missing': not had_marking,
            'absence_status': absence_status,
            'leave_id': leave_rec.id if leave_rec else False,
            'leave_type_name': leave_label or False,
        }
        for f in list(oper_map.values()) + list(admin_map.values()):
            vals[f] = 0.0
        ord_t = xd_t = xn_t = br_t = 0.0
        for slot in group.slot_ids:
            field_name = slot_map.get(slot.name)
            hours = slot_totals.get(slot.id, 0.0)
            # Crossnexion: el DESCANSO (desayuno/almuerzo) se descuenta SIEMPRE
            # la franja completa en dias presentes, marque o no el empleado y
            # aunque haya entrado tarde / salido temprano (la tardanza/salida
            # temprana se reflejan en "a Descontar", no en el descanso). En
            # dias no presentes (falta/licencia/descanso) el descanso es 0.
            if slot.slot_type == 'break':
                hours = slot.duration if absence_status == 'present' else 0.0
            if field_name:
                vals[field_name] = hours
            if slot.slot_type == 'ordinary':
                ord_t += hours
            elif slot.slot_type == 'extra_day':
                xd_t += hours
            elif slot.slot_type == 'extra_night':
                xn_t += hours
            elif slot.slot_type == 'break':
                br_t += hours
        vals['total_ordinary'] = ord_t
        vals['total_extra_day'] = xd_t
        vals['total_extra_night'] = xn_t
        vals['total_break'] = br_t

        # Crossnexion: "a Descontar" por dia (tardanza / salida temprana /
        # ausencia a mitad de dia / falta / licencia no remunerada). La jornada
        # estandar = suma de las franjas ORDINARIAS del turno. Las ordinarias
        # reales (ord_t) ya respetan las tolerancias de entrada/salida.
        expected = sum(
            s.duration for s in group.slot_ids if s.slot_type == 'ordinary')
        has_open = any(a.check_in and not a.check_out for a in atts)
        if absence_status == 'rest':
            expected = 0.0
            deduct = 0.0
        elif absence_status == 'leave':
            deduct = 0.0
        elif absence_status == 'absence':
            deduct = expected
        elif has_open:
            # Dia incompleto (olvido de salida): NO se descuenta, solo se marca;
            # se corrige en "Correccion de Marcaciones".
            deduct = 0.0
        else:  # present completo -> descuento por rangos (tardanza / salida
            # temprana / permiso parcial no remunerado; el remunerado excusa).
            deduct = self._compute_day_deduction(
                employee, group, day, atts, rem_partial, norem_partial)
        vals['expected_ordinary'] = expected
        vals['to_deduct'] = deduct
        vals['has_incomplete_marking'] = has_open and absence_status == 'present'

        # Tolerancia aplicada (gracia absorbida) + Observacion (motivo del
        # descuento/ausencia + horas extras del dia).
        tol_applied = 0.0
        obs_parts = []
        if leave_label:  # permisos / falta / descanso / feriado
            obs_parts.append(leave_label)
        if absence_status == 'present' and atts:
            try:
                off_s, off_e = group.get_shift_official_bounds()
            except Exception:
                off_s = off_e = None
            tm = (getattr(group, 'tolerance_morning_minutes', 0) or 0) / 60.0
            te = (getattr(group, 'tolerance_evening_minutes', 0) or 0) / 60.0
            tzx = self._emp_tz(employee)

            def _dec(dt_utc):
                loc = pytz.utc.localize(dt_utc).astimezone(tzx)
                return loc.hour + loc.minute / 60.0 + loc.second / 3600.0

            try:
                _hle_min, _hlx_min = group.get_hard_limits_minutes()
            except Exception:
                _lg = (getattr(group, 'hard_limit_minutes', 30) or 30)
                _hle_min = _hlx_min = _lg
            hl_e = _hle_min / 60.0
            hl_x = _hlx_min / 60.0
            cis = [a.check_in for a in atts if a.check_in]
            cos = [a.check_out for a in atts if a.check_out]
            late = early = False
            # Si la desviacion supera el limite duro, la tolerancia se pierde (0).
            if cis and off_s is not None:
                d = abs(_dec(min(cis)) - off_s)
                tol_applied += 0.0 if d > hl_e else min(d, tm)
                if (_dec(min(cis)) - off_s) > tm:
                    late = True
            if cos and off_e is not None:
                d = abs(_dec(max(cos)) - off_e)
                tol_applied += 0.0 if d > hl_x else min(d, te)
                if (off_e - _dec(max(cos))) > te:
                    early = True
            if vals['has_incomplete_marking']:
                obs_parts.append(_('Marcacion incompleta (falta salida)'))
            elif deduct > 0.001:
                if late:
                    obs_parts.append(_('Descuento por Tardanza'))
                if early:
                    obs_parts.append(_('Descuento por Salida temprana'))
                if not late and not early:
                    obs_parts.append(_('Descuento'))
            if xd_t > 0.001:
                obs_parts.append(_('Hs Extras Diurnas'))
            if xn_t > 0.001:
                obs_parts.append(_('Hs Extras Nocturnas'))
        vals['tolerance_applied'] = tol_applied
        vals['observation'] = ' / '.join(obs_parts)
        return vals

    def action_recalculate_dashboard(self):
        if self:
            date_from = min(self.mapped('date'))
            date_to = max(self.mapped('date'))
            employee_ids = list(set(self.mapped('employee_id').ids))
        else:
            today = fields.Date.context_today(self)
            date_from = today.replace(day=1)
            if today.month == 12:
                date_to = today.replace(day=31)
            else:
                nxt = today.replace(month=today.month + 1, day=1)
                date_to = nxt - timedelta(days=1)
            employee_ids = None
        try:
            Att = self.env['hr.attendance'].sudo()
            domain = [
                ('check_in', '>=', fields.Datetime.to_datetime(date_from)),
                ('check_in', '<=', fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)),
            ]
            if employee_ids:
                domain.append(('employee_id', 'in', employee_ids))
            atts = Att.search(domain)
            if atts and hasattr(atts, '_recompute_shift_lines'):
                atts._recompute_shift_lines()
        except Exception:
            pass
        n = self.env['hr.attendance.daily.report'].sudo().regenerate(
            date_from=date_from, date_to=date_to, employee_ids=employee_ids,
        )
        msg = _('Tablero recalculado: %d filas generadas para %s a %s') % (n, date_from, date_to)
        if employee_ids:
            msg += _(' (%d empleados)') % len(employee_ids)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Tablero recalculado'), 'message': msg, 'type': 'success', 'sticky': False},
        }

    @api.model
    def action_clear_all_admin(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('Solo administradores pueden ejecutar esta operacion.'))
        count = self.env['hr.attendance.daily.report'].sudo().search_count([])
        self.env.cr.execute('DELETE FROM hr_attendance_daily_report')
        self.invalidate_model()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tablero limpiado'),
                'message': _('Se eliminaron %d filas del tablero diario.') % count,
                'type': 'success',
                'sticky': True,
            },
        }
