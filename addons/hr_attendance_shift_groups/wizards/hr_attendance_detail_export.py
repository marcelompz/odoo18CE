# -*- coding: utf-8 -*-
"""Wizard: Detalle de Entradas/Salidas.

Dos origenes:
  * 'raw'    -> fichajes crudos de zk.machine.attendance (tal cual el reloj,
               para auditoria). Se emparejan por POSICION (E,S,E,S...).
  * 'blocks' -> marcaciones hr.attendance ya procesadas (lo que se paga):
               una fila por bloque, con horas Normal/Extra Diurna/Extra
               Nocturna/Descanso ya clasificadas por las franjas del turno.
"""
import base64
import io
from collections import defaultdict

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class HrAttendanceDetailExport(models.TransientModel):
    _name = 'hr.attendance.detail.export'
    _description = 'Wizard: Exportar Detalle de Entradas/Salidas'

    source = fields.Selection([
        ('raw', 'Crudo del reloj (todos los fichajes)'),
        ('blocks', 'Bloques Odoo (lo que se paga)'),
    ], string='Origen', default='raw', required=True,
        help='Crudo: fichajes tal cual el reloj (auditoria). '
             'Bloques: marcaciones procesadas [entrada, salida] de Odoo, con '
             'horas clasificadas (normal/extra/descanso).')
    date_from = fields.Date(
        string='Fecha desde', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='Fecha hasta', required=True,
        default=fields.Date.context_today)
    employee_ids = fields.Many2many('hr.employee', string='Empleados')
    department_ids = fields.Many2many('hr.department', string='Departamentos')

    file_data = fields.Binary(string='Archivo', readonly=True, attachment=False)
    file_name = fields.Char(string='Nombre archivo', readonly=True)

    # ------------------------------------------------------------------
    def _tz(self):
        return pytz.timezone(self.env.user.tz or 'America/Asuncion')

    def _employee_domain_leaf(self):
        if self.employee_ids:
            return ('employee_id', 'in', self.employee_ids.ids)
        if self.department_ids:
            return ('employee_id.department_id', 'in', self.department_ids.ids)
        return None

    def _daily_reports_by_day(self):
        """{(employee_id, date): hr.attendance.daily.report} del periodo.
        De ahi se toman Descanso (completo) y a Descontar ya calculados."""
        DR = self.env['hr.attendance.daily.report']
        dom = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        leaf = self._employee_domain_leaf()
        if leaf and leaf[0] == 'employee_id':
            dom.append(('employee_id', leaf[1], leaf[2]))
        elif leaf:
            dom.append(('department_id', leaf[1], leaf[2]))
        return {(rr.employee_id.id, rr.date): rr for rr in DR.search(dom)}

    def _shift_group_name(self, emp, day):
        """Nombre del grupo de turno del empleado para ese dia (o vacio)."""
        if emp and hasattr(emp, 'get_active_shift_group'):
            try:
                g = emp.get_active_shift_group(day)
                if g:
                    return g.name or ''
            except Exception:
                pass
        if emp and 'shift_group_id' in emp._fields and emp.shift_group_id:
            return emp.shift_group_id.name or ''
        return ''

    # ------------------------------------------------------------------
    def _collect_raw(self):
        """{employee: {date: [(entrada_local, salida_local|None), ...]}}."""
        tz = self._tz()
        dt_from = fields.Datetime.to_datetime(self.date_from)
        dt_to = fields.Datetime.to_datetime(self.date_to).replace(
            hour=23, minute=59, second=59)
        leaf = self._employee_domain_leaf()
        dom = [('punching_time', '>=', dt_from),
               ('punching_time', '<=', dt_to),
               ('employee_id', '!=', False),
               ('punching_time', '!=', False)]
        if leaf:
            dom.append(leaf)
        raws = self.env['zk.machine.attendance'].search(
            dom, order='punching_time asc')
        tmp = defaultdict(lambda: defaultdict(list))
        for r in raws:
            local = pytz.utc.localize(r.punching_time).astimezone(tz)
            tmp[r.employee_id][local.date()].append(local)
        data = defaultdict(lambda: defaultdict(list))
        for emp, days in tmp.items():
            for d, times in days.items():
                times.sort()
                pairs = []
                for i in range(0, len(times), 2):
                    e = times[i]
                    s = times[i + 1] if i + 1 < len(times) else None
                    pairs.append((e, s))
                data[emp][d] = pairs
        return data

    def _collect_blocks(self):
        """{employee: {date: [hr.attendance, ...]}}."""
        tz = self._tz()
        dt_from = fields.Datetime.to_datetime(self.date_from)
        dt_to = fields.Datetime.to_datetime(self.date_to).replace(
            hour=23, minute=59, second=59)
        leaf = self._employee_domain_leaf()
        dom = [('check_in', '>=', dt_from),
               ('check_in', '<=', dt_to),
               ('employee_id', '!=', False)]
        if leaf:
            dom.append(leaf)
        atts = self.env['hr.attendance'].search(dom, order='check_in asc')
        data = defaultdict(lambda: defaultdict(list))
        for att in atts:
            local = pytz.utc.localize(att.check_in).astimezone(tz)
            data[att.employee_id][local.date()].append(att)
        return data

    # ------------------------------------------------------------------
    def action_export(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_(
                'La libreria Python "xlsxwriter" no esta instalada.'))
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "desde" debe ser anterior a "hasta".'))

        buffer = io.BytesIO()
        wb = xlsxwriter.Workbook(buffer, {'in_memory': True})
        if self.source == 'raw':
            data = self._collect_raw()
            if not data:
                raise UserError(_('No hay fichajes en el periodo/criterio.'))
            self._build_raw(wb, data)
            tag = 'Crudo'
        else:
            data = self._collect_blocks()
            if not data:
                raise UserError(_('No hay marcaciones en el periodo/criterio.'))
            self._build_blocks(wb, data)
            tag = 'Bloques'
        wb.close()
        buffer.seek(0)
        content = buffer.read()
        buffer.close()
        fname = "Detalle_ES_%s_%s_%s.xlsx" % (tag, self.date_from, self.date_to)
        self.write({
            'file_data': base64.b64encode(content),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%s&id=%d&field=file_data'
                   '&filename_field=file_name&download=true' % (
                       self._name, self.id),
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # PDF (QWeb)
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt_h(h):
        m = int(round((h or 0.0) * 60))
        return "%d:%02d" % (m // 60, m % 60)

    def _report_data(self):
        """Datos para el PDF del Detalle (raw o blocks)."""
        self.ensure_one()
        tz = self._tz()

        def hm(dt_):
            return dt_.strftime('%H:%M') if dt_ else ''

        employees = []
        if self.source == 'raw':
            data = self._collect_raw()
            for emp in sorted(data.keys(), key=lambda e: e.name or ''):
                days = data[emp]
                rows = []
                emp_secs = 0.0
                last_day = None
                for d in sorted(days.keys()):
                    last_day = d
                    for (e, s) in days[d]:
                        secs = (s - e).total_seconds() if (e and s) else 0.0
                        emp_secs += secs
                        rows.append({
                            'date': d.strftime('%d/%m/%Y'),
                            'entrada': hm(e),
                            'salida': hm(s) if s else '-- --',
                            'incompl': not s,
                        })
                employees.append({
                    'name': emp.name or '',
                    'dept': emp.department_id.name or '',
                    'group': self._shift_group_name(emp, last_day) if last_day else '',
                    'rows': rows,
                    'total': self._fmt_h(emp_secs / 3600.0),
                })
        else:
            data = self._collect_blocks()
            dr_by = self._daily_reports_by_day()
            for emp in sorted(data.keys(), key=lambda e: e.name or ''):
                days = data[emp]
                rows = []
                tot = {'n': 0.0, 'xd': 0.0, 'xn': 0.0, 'br': 0.0, 'ded': 0.0, 'tol': 0.0}
                grp = ''
                for d in sorted(days.keys()):
                    dr = dr_by.get((emp.id, d))
                    for att in days[d]:
                        ci = pytz.utc.localize(att.check_in).astimezone(tz)
                        co = (pytz.utc.localize(att.check_out).astimezone(tz)
                              if att.check_out else None)
                        if att.shift_group_id:
                            grp = att.shift_group_id.name or grp
                        n = (dr.total_ordinary if dr else att.hours_ordinary) or 0.0
                        xd = (dr.total_extra_day if dr else att.hours_extra_day) or 0.0
                        xn = (dr.total_extra_night if dr else att.hours_extra_night) or 0.0
                        br = (dr.total_break if dr else att.hours_break) or 0.0
                        ded = (dr.to_deduct if dr else 0.0) or 0.0
                        tol = (dr.tolerance_applied if dr else 0.0) or 0.0
                        rows.append({
                            'date': d.strftime('%d/%m/%Y'),
                            'entrada': hm(ci),
                            'salida': hm(co) if co else 'SIN SALIDA',
                            'incompl': not co,
                            'normal': self._fmt_h(n), 'xd': self._fmt_h(xd),
                            'xn': self._fmt_h(xn), 'br': self._fmt_h(br),
                            'ded': self._fmt_h(ded), 'tol': self._fmt_h(tol),
                            'obs': (dr.observation if dr else '') or '',
                        })
                        tot['n'] += n; tot['xd'] += xd; tot['xn'] += xn
                        tot['br'] += br; tot['ded'] += ded; tot['tol'] += tol
                employees.append({
                    'name': emp.name or '',
                    'dept': emp.department_id.name or '',
                    'group': grp,
                    'rows': rows,
                    'tot_n': self._fmt_h(tot['n']), 'tot_xd': self._fmt_h(tot['xd']),
                    'tot_xn': self._fmt_h(tot['xn']), 'tot_br': self._fmt_h(tot['br']),
                    'tot_ded': self._fmt_h(tot['ded']), 'tot_tol': self._fmt_h(tot['tol']),
                })
        return {
            'mode': self.source,
            'employees': employees,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

    def action_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'hr_attendance_shift_groups.action_report_detail_es'
        ).report_action(self)

    # ------------------------------------------------------------------
    def _formats(self, wb):
        return {
            'title': wb.add_format({
                'bold': True, 'font_size': 13, 'font_name': 'Arial'}),
            'hdr': wb.add_format({
                'bold': True, 'border': 1, 'bg_color': '#B4C6E7',
                'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial',
                'text_wrap': True}),
            'cell': wb.add_format({
                'border': 1, 'align': 'center', 'font_name': 'Arial'}),
            'cell_l': wb.add_format({
                'border': 1, 'align': 'left', 'font_name': 'Arial'}),
            'cell_l_red': wb.add_format({
                'border': 1, 'align': 'left', 'font_name': 'Arial',
                'bg_color': '#F4CCCC'}),
            'date': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': 'dd/mm/yyyy',
                'font_name': 'Arial'}),
            'date_red': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': 'dd/mm/yyyy',
                'font_name': 'Arial', 'bg_color': '#F4CCCC'}),
            'hm': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': 'hh:mm',
                'font_name': 'Arial'}),
            'hm_red': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': 'hh:mm',
                'font_name': 'Arial', 'bg_color': '#F4CCCC'}),
            'hours': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': '[h]:mm',
                'font_name': 'Arial'}),
            'hours_extra': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': '[h]:mm',
                'font_name': 'Arial', 'bg_color': '#C6EFCE'}),
            'hours_ded': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': '[h]:mm',
                'font_name': 'Arial', 'bg_color': '#FFC7CE'}),
            'tot_extra': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': '[h]:mm',
                'bold': True, 'bg_color': '#A9D08E', 'font_name': 'Arial'}),
            'tot_ded': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': '[h]:mm',
                'bold': True, 'bg_color': '#F4B0B0', 'font_name': 'Arial'}),
            'tot': wb.add_format({
                'border': 1, 'align': 'center', 'num_format': '[h]:mm',
                'bold': True, 'bg_color': '#F2F2F2', 'font_name': 'Arial'}),
            'totlbl': wb.add_format({
                'border': 1, 'align': 'right', 'bold': True,
                'bg_color': '#F2F2F2', 'font_name': 'Arial'}),
            'miss': wb.add_format({
                'border': 1, 'align': 'center', 'bg_color': '#F4CCCC',
                'font_name': 'Arial'}),
        }

    # ------------------------------------------------------------------
    def _build_raw(self, wb, data):
        f = self._formats(wb)
        max_pairs = 1
        for emp, days in data.items():
            for d, pairs in days.items():
                if len(pairs) > max_pairs:
                    max_pairs = len(pairs)
        max_pairs = min(max_pairs, 6)

        ws = wb.add_worksheet(_('Crudo del reloj')[:31])
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.write(0, 0, "%s - Detalle Entradas/Salidas (Crudo del reloj) - %s a %s" % (
            self.env.company.name or '', self.date_from, self.date_to), f['title'])

        hrow = 2
        headers = [_('Colaborador'), _('Departamento'), _('Grupo de Turno'), _('Dia')]
        for c, h in enumerate(headers):
            ws.write(hrow, c, h, f['hdr'])
        col = len(headers)
        for p in range(max_pairs):
            ws.write(hrow, col, _('Entrada %d') % (p + 1), f['hdr']); col += 1
            ws.write(hrow, col, _('Salida %d') % (p + 1), f['hdr']); col += 1
        col_tot = col
        ws.write(hrow, col_tot, _('Horas dia'), f['hdr'])
        ws.set_column(0, 0, 26); ws.set_column(1, 2, 18); ws.set_column(3, 3, 11)
        ws.set_column(4, col_tot, 10)

        r = hrow + 1
        for emp in sorted(data.keys(), key=lambda e: e.name or ''):
            days = data[emp]
            emp_seconds = 0.0
            for d in sorted(days.keys()):
                pairs = days[d]
                incomplete = any(s is None for (e, s) in pairs)
                tfmt = f['cell_l_red'] if incomplete else f['cell_l']
                dfmt = f['date_red'] if incomplete else f['date']
                hmf = f['hm_red'] if incomplete else f['hm']
                ws.write(r, 0, emp.name or '', tfmt)
                ws.write(r, 1, emp.department_id.name or '', tfmt)
                ws.write(r, 2, self._shift_group_name(emp, d), tfmt)
                ws.write_datetime(r, 3, d, dfmt)
                col = 4
                day_seconds = 0.0
                for p in range(max_pairs):
                    if p < len(pairs):
                        e, s = pairs[p]
                        ws.write_datetime(r, col, e.replace(tzinfo=None), hmf) if e else ws.write(r, col, '', f['cell'])
                        col += 1
                        if s:
                            ws.write_datetime(r, col, s.replace(tzinfo=None), hmf)
                            if e:
                                day_seconds += (s - e).total_seconds()
                        else:
                            ws.write(r, col, _('--'), f['miss'])
                        col += 1
                    else:
                        ws.write(r, col, '', f['cell']); col += 1
                        ws.write(r, col, '', f['cell']); col += 1
                ws.write_number(r, col_tot, day_seconds / 86400.0, f['tot'])
                emp_seconds += day_seconds
                r += 1
            ws.merge_range(r, 0, r, col_tot - 1, _('TOTAL %s') % (emp.name or ''), f['totlbl'])
            ws.write_number(r, col_tot, emp_seconds / 86400.0, f['tot'])
            r += 2
        ws.freeze_panes(hrow + 1, 4)

    # ------------------------------------------------------------------
    def _build_blocks(self, wb, data):
        f = self._formats(wb)
        ws = wb.add_worksheet(_('Bloques Odoo')[:31])
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.write(0, 0, "%s - Detalle Entradas/Salidas (Bloques Odoo - lo que se paga) - %s a %s" % (
            self.env.company.name or '', self.date_from, self.date_to), f['title'])

        hrow = 2
        headers = [_('Colaborador'), _('Departamento'), _('Grupo de Turno'),
                   _('Dia'), _('Entrada'), _('Salida'),
                   _('Normal'), _('Extra Diurna'), _('Extra Nocturna'),
                   _('Descanso'), _('a Descontar'), _('Tolerancia'),
                   _('Observacion')]
        for c, h in enumerate(headers):
            ws.write(hrow, c, h, f['hdr'])
        c_norm, c_xd, c_xn, c_br, c_ded, c_tol, c_obs = 6, 7, 8, 9, 10, 11, 12
        ws.set_column(0, 0, 26); ws.set_column(1, 2, 18); ws.set_column(3, 3, 11)
        ws.set_column(4, 5, 9); ws.set_column(6, 11, 12); ws.set_column(12, 12, 30)

        # Tablero diario por (empleado, dia): de ahi salen Descanso (completo) y
        # a Descontar (tardanza/salida temprana/permiso), ya calculados.
        dr_by = self._daily_reports_by_day()

        tz = self._tz()
        r = hrow + 1
        for emp in sorted(data.keys(), key=lambda e: e.name or ''):
            days = data[emp]
            tot = {'n': 0.0, 'xd': 0.0, 'xn': 0.0, 'br': 0.0, 'ded': 0.0, 'tol': 0.0}
            for d in sorted(days.keys()):
                dr = dr_by.get((emp.id, d))
                for att in days[d]:
                    incomplete = not att.check_out
                    tfmt = f['cell_l_red'] if incomplete else f['cell_l']
                    dfmt = f['date_red'] if incomplete else f['date']
                    hmf = f['hm_red'] if incomplete else f['hm']
                    ci = pytz.utc.localize(att.check_in).astimezone(tz)
                    ws.write(r, 0, emp.name or '', tfmt)
                    ws.write(r, 1, emp.department_id.name or '', tfmt)
                    ws.write(r, 2, (att.shift_group_id.name
                                    or self._shift_group_name(emp, d)), tfmt)
                    ws.write_datetime(r, 3, d, dfmt)
                    ws.write_datetime(r, 4, ci.replace(tzinfo=None), hmf)
                    if att.check_out:
                        co = pytz.utc.localize(att.check_out).astimezone(tz)
                        ws.write_datetime(r, 5, co.replace(tzinfo=None), hmf)
                    else:
                        ws.write(r, 5, _('-- SIN SALIDA --'), f['miss'])
                    n = (dr.total_ordinary if dr else att.hours_ordinary) or 0.0
                    xd = (dr.total_extra_day if dr else att.hours_extra_day) or 0.0
                    xn = (dr.total_extra_night if dr else att.hours_extra_night) or 0.0
                    br = (dr.total_break if dr else att.hours_break) or 0.0
                    ded = (dr.to_deduct if dr else 0.0) or 0.0
                    tol = (dr.tolerance_applied if dr else 0.0) or 0.0
                    ws.write_number(r, c_norm, n / 24.0, f['hours'])
                    ws.write_number(r, c_xd, xd / 24.0, f['hours_extra'])
                    ws.write_number(r, c_xn, xn / 24.0, f['hours_extra'])
                    ws.write_number(r, c_br, br / 24.0, f['hours'])
                    ws.write_number(r, c_ded, ded / 24.0, f['hours_ded'])
                    ws.write_number(r, c_tol, tol / 24.0, f['hours'])
                    ws.write(r, c_obs, (dr.observation if dr else '') or '', f['cell_l'])
                    tot['n'] += n; tot['xd'] += xd; tot['xn'] += xn
                    tot['br'] += br; tot['ded'] += ded; tot['tol'] += tol
                    r += 1
            ws.merge_range(r, 0, r, 5, _('TOTAL %s') % (emp.name or ''), f['totlbl'])
            ws.write_number(r, c_norm, tot['n'] / 24.0, f['tot'])
            ws.write_number(r, c_xd, tot['xd'] / 24.0, f['tot_extra'])
            ws.write_number(r, c_xn, tot['xn'] / 24.0, f['tot_extra'])
            ws.write_number(r, c_br, tot['br'] / 24.0, f['tot'])
            ws.write_number(r, c_ded, tot['ded'] / 24.0, f['tot_ded'])
            ws.write_number(r, c_tol, tot['tol'] / 24.0, f['tot'])
            r += 2
        ws.freeze_panes(hrow + 1, 4)
