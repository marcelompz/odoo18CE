# -*- coding: utf-8 -*-
"""Wizard: Resumen Mensual de Horas por Empleado.

Agrega el tablero diario (hr.attendance.daily.report) por empleado en el
periodo. Columnas: Normal (jornada estandar) / Extra Diurna / Extra Nocturna /
a Descontar / Total, con Total = Normal - a Descontar + Extras.
"""
import base64
import io
from collections import defaultdict

from odoo import fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class HrAttendanceMonthlySummary(models.TransientModel):
    _name = 'hr.attendance.monthly.summary'
    _description = 'Wizard: Resumen Mensual de Horas por Empleado'

    date_from = fields.Date(
        string='Fecha desde', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='Fecha hasta', required=True,
        default=fields.Date.context_today)
    employee_ids = fields.Many2many('hr.employee', string='Empleados')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    shift_group_ids = fields.Many2many('hr.shift.group', string='Grupos de Turno')

    file_data = fields.Binary(string='Archivo', readonly=True, attachment=False)
    file_name = fields.Char(string='Nombre archivo', readonly=True)

    def _collect(self):
        Report = self.env['hr.attendance.daily.report']
        dom = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.employee_ids:
            dom.append(('employee_id', 'in', self.employee_ids.ids))
        elif self.department_ids:
            dom.append(('department_id', 'in', self.department_ids.ids))
        if self.shift_group_ids:
            dom.append(('shift_group_id', 'in', self.shift_group_ids.ids))
        rows = Report.search(dom)
        agg = defaultdict(lambda: {
            'emp': None, 'dept': '', 'group': '',
            'normal': 0.0, 'xd': 0.0, 'xn': 0.0, 'ded': 0.0,
            'faltas': 0, 'incompl': 0, 'present': 0})
        for r in rows:
            a = agg[r.employee_id.id]
            a['emp'] = r.employee_id
            a['dept'] = r.department_id.name or ''
            if r.shift_group_id:
                a['group'] = r.shift_group_id.name or ''
            a['normal'] += r.expected_ordinary or 0.0
            a['xd'] += r.total_extra_day or 0.0
            a['xn'] += r.total_extra_night or 0.0
            a['ded'] += r.to_deduct or 0.0
            if r.absence_status == 'absence':
                a['faltas'] += 1
            if r.has_incomplete_marking:
                a['incompl'] += 1
            if r.absence_status == 'present':
                a['present'] += 1
        return agg

    def action_export(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_('La libreria "xlsxwriter" no esta instalada.'))
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "desde" debe ser anterior a "hasta".'))
        agg = self._collect()
        if not agg:
            raise UserError(_('No hay datos del tablero en el periodo. '
                              'Regenere el Tablero Diario primero.'))
        buffer = io.BytesIO()
        wb = xlsxwriter.Workbook(buffer, {'in_memory': True})
        self._build(wb, agg)
        wb.close()
        buffer.seek(0)
        content = buffer.read()
        buffer.close()
        fname = "Resumen_Mensual_%s_%s.xlsx" % (self.date_from, self.date_to)
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
    def _fmt_hours(h):
        """Horas decimales -> 'H:MM'."""
        m = int(round((h or 0.0) * 60))
        return "%d:%02d" % (m // 60, m % 60)

    def _report_rows(self):
        """Filas listas para el PDF (horas ya formateadas H:MM) + totales.
        Llamado desde el template QWeb."""
        self.ensure_one()
        agg = self._collect()
        rows = []
        tot = {'normal': 0.0, 'xd': 0.0, 'xn': 0.0, 'ded': 0.0, 'total': 0.0,
               'faltas': 0, 'incompl': 0}
        for a in sorted(agg.values(),
                        key=lambda x: ((x['group'] or ''), (x['emp'].name or ''))):
            total = a['normal'] - a['ded'] + a['xd'] + a['xn']
            rows.append({
                'name': a['emp'].name or '', 'dept': a['dept'],
                'group': a['group'],
                'normal': self._fmt_hours(a['normal']),
                'xd': self._fmt_hours(a['xd']),
                'xn': self._fmt_hours(a['xn']),
                'ded': self._fmt_hours(a['ded']),
                'total': self._fmt_hours(total),
                'faltas': a['faltas'], 'incompl': a['incompl'],
            })
            tot['normal'] += a['normal']; tot['xd'] += a['xd']
            tot['xn'] += a['xn']; tot['ded'] += a['ded']; tot['total'] += total
            tot['faltas'] += a['faltas']; tot['incompl'] += a['incompl']
        totals = {
            'normal': self._fmt_hours(tot['normal']),
            'xd': self._fmt_hours(tot['xd']), 'xn': self._fmt_hours(tot['xn']),
            'ded': self._fmt_hours(tot['ded']),
            'total': self._fmt_hours(tot['total']),
            'faltas': tot['faltas'], 'incompl': tot['incompl'],
        }
        return {'rows': rows, 'totals': totals}

    def action_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'hr_attendance_shift_groups.action_report_monthly_summary'
        ).report_action(self)

    def _build(self, wb, agg):
        title = wb.add_format({
            'bold': True, 'font_size': 13, 'font_name': 'Arial'})
        info = wb.add_format({
            'italic': True, 'font_size': 10, 'font_name': 'Arial'})
        hdr = wb.add_format({
            'bold': True, 'border': 1, 'bg_color': '#B4C6E7', 'align': 'center',
            'valign': 'vcenter', 'font_name': 'Arial', 'text_wrap': True})
        cell_l = wb.add_format({
            'border': 1, 'align': 'left', 'font_name': 'Arial'})
        hours = wb.add_format({
            'border': 1, 'align': 'center', 'num_format': '[h]:mm',
            'font_name': 'Arial'})
        hours_tot = wb.add_format({
            'border': 1, 'align': 'center', 'num_format': '[h]:mm', 'bold': True,
            'bg_color': '#E2EFDA', 'font_name': 'Arial'})
        extra_fmt = wb.add_format({
            'border': 1, 'align': 'center', 'num_format': '[h]:mm',
            'bg_color': '#C6EFCE', 'font_name': 'Arial'})
        ded_fmt = wb.add_format({
            'border': 1, 'align': 'center', 'num_format': '[h]:mm',
            'bg_color': '#FFC7CE', 'font_name': 'Arial'})
        intf = wb.add_format({
            'border': 1, 'align': 'center', 'font_name': 'Arial'})
        totlbl = wb.add_format({
            'border': 1, 'align': 'right', 'bold': True, 'bg_color': '#F2F2F2',
            'font_name': 'Arial'})
        tot = wb.add_format({
            'border': 1, 'align': 'center', 'num_format': '[h]:mm', 'bold': True,
            'bg_color': '#F2F2F2', 'font_name': 'Arial'})
        toti = wb.add_format({
            'border': 1, 'align': 'center', 'bold': True, 'bg_color': '#F2F2F2',
            'font_name': 'Arial'})

        ws = wb.add_worksheet(_('Resumen Mensual')[:31])
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.write(0, 0, "%s - Resumen Mensual de Horas - %s a %s" % (
            self.env.company.name or '', self.date_from, self.date_to), title)
        ws.write(1, 0, _('Total = Normal - a Descontar + Extra Diurna + '
                         'Extra Nocturna'), info)

        hrow = 3
        headers = [_('Colaborador'), _('Departamento'), _('Grupo de Turno'),
                   _('Normal'), _('Extra Diurna'), _('Extra Nocturna'),
                   _('a Descontar'), _('Total'), _('Faltas'), _('Incompletos')]
        for c, h in enumerate(headers):
            ws.write(hrow, c, h, hdr)
        ws.set_column(0, 0, 28); ws.set_column(1, 2, 18)
        ws.set_column(3, 7, 13); ws.set_column(8, 9, 10)

        r = hrow + 1
        first = r
        s_norm = s_xd = s_xn = s_ded = s_tot = 0.0
        s_falt = s_inc = 0
        ordered = sorted(agg.values(),
                         key=lambda a: ((a['group'] or ''), (a['emp'].name or '')))
        for a in ordered:
            total = a['normal'] - a['ded'] + a['xd'] + a['xn']
            ws.write(r, 0, a['emp'].name or '', cell_l)
            ws.write(r, 1, a['dept'], cell_l)
            ws.write(r, 2, a['group'], cell_l)
            ws.write_number(r, 3, a['normal'] / 24.0, hours)
            ws.write_number(r, 4, a['xd'] / 24.0, extra_fmt)
            ws.write_number(r, 5, a['xn'] / 24.0, extra_fmt)
            ws.write_number(r, 6, a['ded'] / 24.0, ded_fmt)
            ws.write_number(r, 7, total / 24.0, hours_tot)
            ws.write_number(r, 8, a['faltas'], intf)
            ws.write_number(r, 9, a['incompl'], intf)
            s_norm += a['normal']; s_xd += a['xd']; s_xn += a['xn']
            s_ded += a['ded']; s_tot += total
            s_falt += a['faltas']; s_inc += a['incompl']
            r += 1
        if r > first:
            ws.merge_range(r, 0, r, 2, _('TOTAL GENERAL'), totlbl)
            ws.write_number(r, 3, s_norm / 24.0, tot)
            ws.write_number(r, 4, s_xd / 24.0, tot)
            ws.write_number(r, 5, s_xn / 24.0, tot)
            ws.write_number(r, 6, s_ded / 24.0, tot)
            ws.write_number(r, 7, s_tot / 24.0, tot)
            ws.write_number(r, 8, s_falt, toti)
            ws.write_number(r, 9, s_inc, toti)
        ws.freeze_panes(hrow + 1, 3)
