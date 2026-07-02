# -*- coding: utf-8 -*-
import base64
import io
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


PERIOD_SELECTION = [
    ('week', 'Semana'),
    ('fortnight', 'Quincena'),
    ('month', 'Mes'),
    ('custom', 'Rango Personalizado'),
]


class HrAttendanceShiftExport(models.TransientModel):
    _name = 'hr.attendance.shift.export'
    _description = 'Wizard: Exportar tablero por turnos a Excel'

    period_type = fields.Selection(PERIOD_SELECTION, string='Período', default='month', required=True)
    date_from = fields.Date(string='Fecha desde', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='Fecha hasta', required=True,
                          default=lambda self: fields.Date.context_today(self).replace(day=28))
    employee_ids = fields.Many2many('hr.employee', string='Empleados',
        help='Si se deja vacío, se exportan todos los empleados con asistencia en el período.')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    shift_group_ids = fields.Many2many('hr.shift.group', string='Grupos de Turno')
    include_empty_days = fields.Boolean(string='Incluir días sin asistencia', default=True)

    file_data = fields.Binary(string='Archivo', readonly=True, attachment=False)
    file_name = fields.Char(string='Nombre archivo', readonly=True)

    @api.onchange('period_type')
    def _onchange_period_type(self):
        today = fields.Date.context_today(self)
        if self.period_type == 'week':
            start = today - timedelta(days=today.weekday())
            self.date_from = start
            self.date_to = start + timedelta(days=6)
        elif self.period_type == 'fortnight':
            if today.day <= 15:
                self.date_from = today.replace(day=1)
                self.date_to = today.replace(day=15)
            else:
                self.date_from = today.replace(day=16)
                # último día del mes
                if today.month == 12:
                    self.date_to = today.replace(day=31)
                else:
                    nxt = today.replace(month=today.month + 1, day=1)
                    self.date_to = nxt - timedelta(days=1)
        elif self.period_type == 'month':
            self.date_from = today.replace(day=1)
            if today.month == 12:
                self.date_to = today.replace(day=31)
            else:
                nxt = today.replace(month=today.month + 1, day=1)
                self.date_to = nxt - timedelta(days=1)

    # ------------------------------------------------------------------
    # Acción principal
    # ------------------------------------------------------------------
    def action_export(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_(
                'La librería Python "xlsxwriter" no está instalada. '
                'Ejecute: pip install xlsxwriter'
            ))
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "desde" debe ser anterior a "hasta".'))

        data = self._collect_data()
        if not data['rows']:
            raise UserError(_('No hay datos para exportar en el período/criterio seleccionado.'))

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        self._build_workbook(workbook, data)
        workbook.close()
        buffer.seek(0)
        content = buffer.read()
        buffer.close()

        company_name = (self.env.company.name or 'Empresa').replace(' ', '_')
        file_name = "Tablero_Turnos_%s_%s_%s.xlsx" % (
            company_name, self.date_from, self.date_to
        )
        self.write({
            'file_data': base64.b64encode(content),
            'file_name': file_name,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%s&id=%d&field=file_data&filename_field=file_name&download=true' % (
                self._name, self.id),
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # Recolección de datos
    # ------------------------------------------------------------------
    def _collect_data(self):
        """Devuelve un dict con la información agregada por (empleado, día).
        Estructura:
          {
            'rows': [
                {
                    'employee': hr.employee,
                    'shift_group': hr.shift.group,
                    'days': {date: {slot_id: hours, ...}},
                },
                ...
            ],
            'date_from', 'date_to', 'company': res.company,
          }
        """
        Attendance = self.env['hr.attendance']
        domain = [
            ('check_in', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('check_in', '<=', fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)),
        ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))
        if self.shift_group_ids:
            domain.append(('shift_group_id', 'in', self.shift_group_ids.ids))
        attendances = Attendance.search(domain, order='employee_id, check_in')

        # Agrupar por empleado
        per_employee = defaultdict(lambda: {
            'shift_group': None,
            'days': defaultdict(lambda: defaultdict(float)),
        })
        for att in attendances:
            emp = att.employee_id
            if not emp:
                continue
            entry = per_employee[emp.id]
            entry['employee'] = emp
            entry['shift_group'] = att.shift_group_id or entry['shift_group']
            for line in att.shift_line_ids:
                entry['days'][line.date][line.slot_id.id] += line.hours_worked

        # Construir filas finales
        rows = []
        for emp_id, entry in per_employee.items():
            rows.append({
                'employee': entry['employee'],
                'shift_group': entry['shift_group'],
                'days': entry['days'],
            })
        rows.sort(key=lambda r: (r['shift_group'].name if r['shift_group'] else '', r['employee'].name or ''))

        return {
            'rows': rows,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company': self.env.company,
            'include_empty_days': self.include_empty_days,
        }

    # ------------------------------------------------------------------
    # Construcción del XLSX (replica el modelo de planilla)
    # ------------------------------------------------------------------
    def _build_workbook(self, workbook, data):
        """Genera una hoja por cada Grupo de Turno detectado, con encabezados y
        columnas dinámicas según las franjas del grupo. Replica el modelo
        proporcionado (Modelo_de_tablero_por_Turnos.xlsx)."""
        # Formatos
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
            'font_name': 'Arial',
        })
        info_fmt = workbook.add_format({
            'italic': True, 'font_size': 10, 'font_name': 'Arial', 'align': 'left',
        })
        header_group_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'bg_color': '#D9E1F2', 'font_name': 'Arial',
        })
        header_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'bg_color': '#B4C6E7', 'font_name': 'Arial', 'text_wrap': True,
        })
        text_fmt = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_name': 'Arial',
        })
        date_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': 'dd-mm-yyyy', 'font_name': 'Arial',
        })
        time_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': 'h:mm', 'font_name': 'Arial',
        })
        time_extra_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#92D050',
        })
        time_break_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': 'h:mm', 'font_name': 'Arial', 'bg_color': '#FFD966',
        })
        total_fmt = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
            'num_format': '[h]:mm', 'font_name': 'Arial', 'bg_color': '#F2F2F2',
        })
        total_label_fmt = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'font_name': 'Arial', 'bg_color': '#F2F2F2',
        })

        # Agrupar filas por shift_group (una hoja por grupo)
        groups_seen = {}
        for row in data['rows']:
            g = row['shift_group']
            if not g:
                continue
            groups_seen.setdefault(g.id, {'group': g, 'rows': []})['rows'].append(row)

        if not groups_seen:
            ws = workbook.add_worksheet('Sin Datos')
            ws.write(0, 0, 'No hay asistencias con grupo de turno asignado en el período.', info_fmt)
            return

        for gid, payload in groups_seen.items():
            group = payload['group']
            grp_rows = payload['rows']
            self._build_sheet(
                workbook, group, grp_rows, data,
                title_fmt, info_fmt, header_group_fmt, header_fmt,
                text_fmt, date_fmt, time_fmt, time_extra_fmt, time_break_fmt,
                total_fmt, total_label_fmt,
            )

    def _build_sheet(self, workbook, group, rows, data,
                     title_fmt, info_fmt, header_group_fmt, header_fmt,
                     text_fmt, date_fmt, time_fmt, time_extra_fmt, time_break_fmt,
                     total_fmt, total_label_fmt):
        """Construye una hoja para un grupo de turno con todas sus filas (empleado x día)."""
        sheet_name = (group.name or 'Grupo')[:28]
        ws = workbook.add_worksheet(sheet_name)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_paper(9)  # A4

        slots = group.get_visible_slots()
        all_slot_ids = list(slots.ids)
        slot_by_id = {s.id: s for s in slots}

        # Encabezado de empresa y período (filas 0-1)
        company = data['company'].name or ''
        period_label = "%s - %s" % (data['date_from'], data['date_to'])
        total_cols = 2 + len(slots) + 3  # Colaborador, Día, slots, Total Jornada, Extra Diurno, Extra Nocturno
        ws.merge_range(0, 0, 0, total_cols - 1, "%s — Tablero por Turnos (%s)" % (company, group.name), title_fmt)
        ws.merge_range(1, 0, 1, total_cols - 1, "Período: %s" % period_label, info_fmt)
        ws.set_row(0, 22)
        ws.set_row(1, 16)

        # Fila 3 (índice 2): grupos de columnas
        # Fila 4 (índice 3): rangos horarios y nombres
        header_row_top = 2
        header_row_bottom = 3

        ws.merge_range(header_row_top, 0, header_row_bottom, 0, 'Colaborador', header_fmt)
        ws.merge_range(header_row_top, 1, header_row_bottom, 1, 'Día', header_fmt)

        col = 2
        for slot in slots:
            ws.write(header_row_top, col, slot.name, header_group_fmt)
            from_h = int(slot.time_from)
            from_m = int(round((slot.time_from - from_h) * 60))
            to_h = int(slot.time_to)
            to_m = int(round((slot.time_to - to_h) * 60))
            range_label = "%02d:%02d - %02d:%02d" % (from_h, from_m, to_h, to_m)
            ws.write(header_row_bottom, col, range_label, header_fmt)
            col += 1

        # Columnas de totales (Diurno, Extra Diurno, Extra Nocturno)
        ws.merge_range(header_row_top, col, header_row_bottom, col, 'Total Jornada', header_fmt); col_diurno = col; col += 1
        ws.merge_range(header_row_top, col, header_row_bottom, col, 'Total Extra Diurno', header_fmt); col_xday = col; col += 1
        ws.merge_range(header_row_top, col, header_row_bottom, col, 'Total Extra Nocturno', header_fmt); col_xnight = col

        # Anchos de columna
        ws.set_column(0, 0, 28)
        ws.set_column(1, 1, 12)
        for c in range(2, 2 + len(slots)):
            ws.set_column(c, c, 14)
        ws.set_column(col_diurno, col_xnight, 18)
        ws.set_row(header_row_top, 22)
        ws.set_row(header_row_bottom, 26)

        # Determinar columnas por tipo (para totales)
        ordinary_cols = []
        extra_day_cols = []
        extra_night_cols = []
        for idx, slot in enumerate(slots):
            c = 2 + idx
            if slot.slot_type == 'ordinary':
                ordinary_cols.append(c)
            elif slot.slot_type == 'extra_day':
                extra_day_cols.append(c)
            elif slot.slot_type == 'extra_night':
                extra_night_cols.append(c)

        # Generar lista de fechas del período
        all_dates = []
        d = data['date_from']
        while d <= data['date_to']:
            all_dates.append(d)
            d += timedelta(days=1)

        # Datos
        current_row = header_row_bottom + 1
        first_data_row = current_row

        for entry in rows:
            emp = entry['employee']
            days_data = entry['days']
            for date in all_dates:
                if not data['include_empty_days'] and date not in days_data:
                    continue
                ws.write(current_row, 0, emp.name or '', text_fmt)
                ws.write_datetime(current_row, 1, date, date_fmt)
                day_slots = days_data.get(date, {})
                for idx, slot in enumerate(slots):
                    c = 2 + idx
                    hours = day_slots.get(slot.id, 0.0)
                    fmt = time_fmt
                    if slot.slot_type == 'extra_day':
                        fmt = time_extra_fmt
                    elif slot.slot_type == 'extra_night':
                        fmt = time_extra_fmt
                    elif slot.slot_type == 'break':
                        fmt = time_break_fmt
                    if hours > 0:
                        ws.write_number(current_row, c, hours / 24.0, fmt)
                    else:
                        ws.write_number(current_row, c, 0.0, fmt)
                # Fórmulas de totales por fila
                ws.write_formula(current_row, col_diurno,
                    self._sum_formula(current_row, ordinary_cols), total_fmt, 0.0)
                ws.write_formula(current_row, col_xday,
                    self._sum_formula(current_row, extra_day_cols), total_fmt, 0.0)
                ws.write_formula(current_row, col_xnight,
                    self._sum_formula(current_row, extra_night_cols), total_fmt, 0.0)
                current_row += 1

        last_data_row = current_row - 1

        # Fila de totales por columna
        if last_data_row >= first_data_row:
            ws.merge_range(current_row, 0, current_row, 1, 'TOTAL', total_label_fmt)
            for c in range(2, col_xnight + 1):
                col_letter = xlsxwriter.utility.xl_col_to_name(c)
                formula = '=SUM(%s%d:%s%d)' % (col_letter, first_data_row + 1, col_letter, last_data_row + 1)
                ws.write_formula(current_row, c, formula, total_fmt, 0.0)
            ws.set_row(current_row, 22)

        ws.freeze_panes(header_row_bottom + 1, 2)

    @staticmethod
    def _sum_formula(row, cols):
        if not cols:
            return '=0'
        # Construye =A5+B5+... usando letras de columna y la fila (1-indexed)
        parts = []
        for c in cols:
            parts.append('%s%d' % (xlsxwriter.utility.xl_col_to_name(c), row + 1))
        return '=' + '+'.join(parts)
