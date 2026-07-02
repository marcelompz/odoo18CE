# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import calendar
from datetime import date
import io
import logging
import xlsxwriter

_logger = logging.getLogger(__name__)

class HrPayrollReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.report.wizard'

    def _generate_mtess_monthly_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Planilla Mensual')

        # Estilos
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})

        def _get_line_total(slip, code):
            line = slip.line_ids.filtered(lambda l: l.code == code)
            return sum(line.mapped('total')) if line else 0.0

        def _get_hours_by_weekday(resource_calendar):
            if not resource_calendar or not resource_calendar.attendance_ids:
                return {0: 8, 1: 8, 2: 8, 3: 8, 4: 8, 5: 4, 6: 0}
            hours = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
            for attendance in resource_calendar.attendance_ids:
                try:
                    weekday = int(attendance.dayofweek)
                except (TypeError, ValueError):
                    continue
                hours[weekday] += max(attendance.hour_to - attendance.hour_from, 0)
            return hours

        # Encabezados
        base_headers = ['No de Orden', 'NOMBRES Y APELLIDOS', 'No. C.I.']
        day_headers = [str(day) for day in range(1, 32)]
        concepts = self.env['hr.payroll.mtess.concept'].search(
            [('active', '=', True)],
            order='sequence, id'
        )
        group_rank = {}
        for c in concepts:
            if c.grupo not in group_rank:
                group_rank[c.grupo] = c.sequence
            else:
                group_rank[c.grupo] = min(group_rank[c.grupo], c.sequence)
        concepts = sorted(
            concepts,
            key=lambda c: (group_rank.get(c.grupo, 99), c.sequence, c.id),
        )
        concept_headers = [concept.name for concept in concepts]
        tail_headers = concept_headers
        headers = base_headers + day_headers + tail_headers

        for col in range(len(base_headers)):
            sheet.write(0, col, '', header_format)

        weekday_map = {0: 'L', 1: 'M', 2: 'M', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
        date_from = self.date_from
        date_to = self.date_to
        if self.payslip_run_id:
            date_from = self.payslip_run_id.date_start or date_from
            date_to = self.payslip_run_id.date_end or date_to
        if not date_from or not date_to:
            raise UserError(_("Debe indicar un lote de nómina o un rango de fechas válido."))

        month_start = date_from.replace(day=1)
        days_in_month = calendar.monthrange(month_start.year, month_start.month)[1]
        start_day_col = len(base_headers)
        for day in range(1, 32):
            col = start_day_col + day - 1
            if day <= days_in_month:
                weekday = date(month_start.year, month_start.month, day).weekday()
                sheet.write(0, col, weekday_map.get(weekday, ''), header_format)
            else:
                sheet.write(0, col, '', header_format)

        salary_start = start_day_col + 31
        salary_end = salary_start
        extras_start = salary_start
        extras_end = salary_start
        benefits_start = salary_start
        benefits_end = salary_start
        total_col = salary_start

        concept_index = {c.id: i for i, c in enumerate(concepts)}
        fixed_index = {}
        for c in concepts:
            if c.fixed_code:
                fixed_index[c.fixed_code] = concept_index[c.id]

        def _group_bounds(group_key):
            indexes = [concept_index[c.id] for c in concepts if c.grupo == group_key]
            if not indexes:
                return None
            return min(indexes), max(indexes)

        salary_bounds = _group_bounds('SALARIO')
        extras_bounds = _group_bounds('HORAS_EXTRAS')
        benefits_bounds = _group_bounds('BENEFICIOS')
        total_bounds = _group_bounds('TOTAL')

        if salary_bounds:
            salary_start = start_day_col + 31 + salary_bounds[0]
            salary_end = start_day_col + 31 + salary_bounds[1]
            sheet.merge_range(0, salary_start, 0, salary_end, 'SALARIO', header_format)
        if extras_bounds:
            extras_start = start_day_col + 31 + extras_bounds[0]
            extras_end = start_day_col + 31 + extras_bounds[1]
            sheet.merge_range(0, extras_start, 0, extras_end, 'HORAS EXTRAS', header_format)
        if benefits_bounds:
            benefits_start = start_day_col + 31 + benefits_bounds[0]
            benefits_end = start_day_col + 31 + benefits_bounds[1]
            sheet.merge_range(0, benefits_start, 0, benefits_end, 'BENEFICIOS SOCIALES', header_format)
        if total_bounds:
            total_start = start_day_col + 31 + total_bounds[0]
            total_end = start_day_col + 31 + total_bounds[1]
            if total_start == total_end:
                sheet.write(0, total_start, 'TOTAL GENERAL', header_format)
            else:
                sheet.merge_range(0, total_start, 0, total_end, 'TOTAL GENERAL', header_format)

        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)

        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 35)
        sheet.set_column(2, 2, 12)
        sheet.set_column(start_day_col, start_day_col + 30, 4)
        tail_end = salary_start + max(len(tail_headers) - 1, 0)
        sheet.set_column(salary_start, tail_end, 18)

        # Obtener nominas del periodo
        domain = [
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id)
        ]
        if self.payslip_run_id:
            domain.append(('payslip_run_id', '=', self.payslip_run_id.id))
        else:
            domain.extend([
                ('date_to', '>=', date_from),
                ('date_to', '<=', date_to)
            ])
        payslips = self.env['hr.payslip'].search(domain)

        row = 2
        idx = 1
        for slip in payslips:
            employee = slip.employee_id
            contract = slip.contract_id

            salario_base = _get_line_total(slip, 'BASIC') or (contract.wage if contract else 0.0)
            he_50 = _get_line_total(slip, 'HE_DIURNA')
            he_100 = _get_line_total(slip, 'HE_NOCTURNA')
            he_monto = he_50 + he_100

            wage_type = contract.wage_type if contract and hasattr(contract, 'wage_type') else 'monthly'
            forma_pago = 'Mensual' if wage_type == 'monthly' else 'Jornal'
            importe_unitario = (contract.wage / 30) if (contract and wage_type == 'monthly') else (contract.wage if contract else 0.0)

            sheet.write(row, 0, idx, number_format)
            sheet.write(row, 1, employee.name, data_format)
            sheet.write(row, 2, employee.identification_id or '', data_format)

            hours_by_weekday = _get_hours_by_weekday(contract.resource_calendar_id if contract else None)
            for day in range(1, 32):
                col = start_day_col + day - 1
                if day > days_in_month:
                    value = ''
                else:
                    current_date = date(month_start.year, month_start.month, day)
                    if current_date < date_from or current_date > date_to:
                        value = ''
                    elif contract and contract.date_start and current_date < contract.date_start:
                        value = ''
                    elif contract and contract.date_end and current_date > contract.date_end:
                        value = ''
                    else:
                        hours = hours_by_weekday.get(current_date.weekday(), 0)
                        if hours <= 0:
                            value = 'D'
                        elif float(hours).is_integer():
                            value = int(hours)
                        else:
                            value = hours
                sheet.write(row, col, value, data_format)

            dias_trab = sum(line.number_of_days for line in slip.worked_days_line_ids if line.code == 'WORK100')
            horas_trab = sum(line.number_of_hours for line in slip.worked_days_line_ids if line.code == 'WORK100')

            tail_col = salary_start
            total_included = 0.0
            for idx, concept in enumerate(concepts):
                value = 0.0
                if concept.value_type == 'fixed':
                    if concept.fixed_code == 'FORMA_PAGO':
                        value = forma_pago
                    elif concept.fixed_code == 'IMPORTE_UNITARIO':
                        value = importe_unitario
                    elif concept.fixed_code == 'DIAS_TRAB':
                        value = dias_trab
                    elif concept.fixed_code == 'HORAS_TRAB':
                        value = horas_trab
                    elif concept.fixed_code == 'IMPORTE':
                        value = salario_base
                    elif concept.fixed_code == 'HE_50':
                        value = he_50
                    elif concept.fixed_code == 'HE_100':
                        value = he_100
                    elif concept.fixed_code == 'HE_IMPORTE':
                        value = he_monto
                    elif concept.fixed_code == 'TOTAL_GENERAL':
                        value = total_included
                else:
                    value = self._get_mtess_concept_value(slip, concept)

                if concept.include_in_total and concept.fixed_code != 'TOTAL_GENERAL':
                    total_included += value if isinstance(value, (int, float)) else 0.0

                col = tail_col + idx
                if isinstance(value, str):
                    sheet.write(row, col, value, data_format)
                else:
                    sheet.write(row, col, value, number_format)

            idx += 1
            row += 1

        workbook.close()
        output.seek(0)

        filename = f'MTESS_Planilla_Mensual_{date_from}_{date_to}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'hr.payroll.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_mtess_employees_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Libro Empleados')

        # Estilos
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})

        # Encabezados
        headers = [
            'No.',
            'Apellidos, Nombres (Orden Alfabético)',
            'Nacionalidad',
            'C.I.No.',
            'No. De Hijos',
            'Profesión',
            'Cargo Desempeñado',
            'Fecha de Entrada',
            'Fecha de Salida',
            'Motivo de Salida',
            'Observaciones',
            'Fecha de Nac.',
            'Situac. Escolar',
            'Cert. Capac. Exp. En Fecha',
            'Horario de Trabajo',
        ]

        for col in range(11):
            sheet.write(0, col, '', header_format)
        sheet.merge_range(0, 11, 0, 14, 'MENORES', header_format)

        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)
            sheet.set_column(col, col, 20)
        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 35)
        sheet.set_column(6, 6, 30)
        sheet.set_column(10, 10, 25)

        # Obtener contratos activos o del periodo
        # Se incluyen empleados con contrato activo o que hayan tenido contrato en el periodo
        domain = [
            ('state', 'in', ['open', 'close']),
            ('company_id', '=', self.company_id.id),
            '|',
            ('date_end', '>=', self.date_from),
            ('date_end', '=', False),
        ]
        # Filtrar también por fecha de inicio para no traer futuros
        contracts = self.env['hr.contract'].search(domain).filtered(lambda c: c.date_start <= self.date_to)

        row = 2
        idx = 1
        for contract in contracts:
            employee = contract.employee_id
            dependents = employee.dependent_ids.filtered(
                lambda d: d.is_active and d.relationship in ('hijo', 'hijastro')
            )
            minor = dependents[:1]
            minor_birth = minor.birth_date if minor else ''
            minor_school = 'Estudiante' if minor and minor.is_student else ''

            num_hijos = employee.dependent_count if 'dependent_count' in employee._fields else employee.children
            profesion = employee.job_title or ''
            cargo = employee.job_id.name if employee.job_id else employee.job_title or ''
            horario = contract.resource_calendar_id.name if contract.resource_calendar_id else ''

            sheet.write(row, 0, idx, number_format)
            sheet.write(row, 1, employee.name, data_format)
            sheet.write(row, 2, employee.country_id.name or '', data_format)
            sheet.write(row, 3, employee.identification_id or '', data_format)
            sheet.write(row, 4, num_hijos or 0, number_format)
            sheet.write(row, 5, profesion, data_format)
            sheet.write(row, 6, cargo, data_format)
            sheet.write(row, 7, contract.date_start, date_format)
            sheet.write(row, 8, contract.date_end or '', date_format)
            sheet.write(row, 9, '', data_format)
            sheet.write(row, 10, '', data_format)
            sheet.write(row, 11, minor_birth or '', date_format)
            sheet.write(row, 12, minor_school, data_format)
            sheet.write(row, 13, '', data_format)
            sheet.write(row, 14, horario, data_format)

            idx += 1
            row += 1

        workbook.close()
        output.seek(0)
        
        filename = f'MTESS_Libro_Empleados_{self.date_from}_{self.date_to}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'hr.payroll.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _get_salary_line_total(self, slip, code):
        """Helper para obtener total de línea salarial por código"""
        if not slip:
            return 0.0
        line = slip.line_ids.filtered(lambda l: l.code == code)
        if line:
            return sum(line.mapped('total'))
        return 0.0

    def _parse_code_list(self, code_list):
        return [code.strip() for code in (code_list or '').split(',') if code.strip()]

    def _get_mtess_concept_value(self, slip, concept):
        codes = self._parse_code_list(concept.code_list)
        exclude_codes = self._parse_code_list(concept.exclude_code_list)
        if not codes:
            return 0.0
        totals = [self._get_salary_line_total(slip, code) for code in codes]
        if concept.compute_mode == 'first_nonzero':
            value = 0.0
            for total in totals:
                if total:
                    value = total
                    break
        else:
            value = sum(totals)
        if exclude_codes:
            value -= sum(self._get_salary_line_total(slip, code) for code in exclude_codes)
        if concept.use_abs:
            value = abs(value)
        return value

    def _get_payroll_summary_concept_value(self, slip, concept):
        codes = self._parse_code_list(concept.code_list)
        if not codes:
            return 0.0
        totals = [self._get_salary_line_total(slip, code) for code in codes]
        if concept.compute_mode == 'first_nonzero':
            value = 0.0
            for total in totals:
                if total:
                    value = total
                    break
        else:
            value = sum(totals)
        if concept.use_abs:
            value = abs(value)
        return value

    def _generate_mtess_vacations_report(self):
        """Genera el Libro Registro de Vacaciones MTESS"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Libro Vacaciones')

        # Estilos
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})

        # Encabezados del Libro de Vacaciones
        headers = [
            'N° Patronal', 'Nombre o Razón Social', 'Domicilio',
            'Nombre y Apellido', 'Cédula Identidad', 'Fecha Ingreso',
            'Año de Servicio', 'Período de Vacaciones', 'Fecha Inicio Vacaciones',
            'Fecha Fin Vacaciones', 'Días Otorgados', 'Días Gozados', 'Días Pendientes',
            'Monto Pago Vacaciones', 'Estado', 'Observaciones'
        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 18)

        # Obtener empleados activos con contratos
        employees = self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True)
        ])

        row = 1
        for employee in employees:
            contract = employee.contract_id
            if not contract or contract.state != 'open':
                continue

            # Buscar solicitudes de vacaciones (hr.leave) del período
            # Buscar por nombre que contenga "vacaciones" (el modelo hr.leave.type no tiene campo 'code')
            leave_type = self.env['hr.leave.type'].search([
                ('name', 'ilike', 'vacaciones')
            ], limit=1)

            if leave_type:
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('date_from', '>=', self.date_from),
                    ('date_to', '<=', self.date_to),
                    ('state', '=', 'validate')
                ])
            else:
                # Si no se encuentra tipo de vacaciones específico, buscar todos los tipos validados
                # Esto incluirá vacaciones si existen en el sistema
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '>=', self.date_from),
                    ('date_to', '<=', self.date_to),
                    ('state', '=', 'validate')
                ])
                # Filtrar solo los que parecen ser vacaciones por nombre
                leaves = leaves.filtered(lambda l: 'vacaciones' in (l.holiday_status_id.name or '').lower())

            # Si no hay vacaciones en el período, registrar información del empleado igual
            if not leaves:
                # Calcular años de servicio
                years_service = 0
                if contract.date_start:
                    delta = self.date_to - contract.date_start
                    years_service = delta.days / 365.25

                sheet.write(row, 0, self.company_id.company_registry or '', data_format)
                sheet.write(row, 1, self.company_id.name, data_format)
                sheet.write(row, 2, self.company_id.street or '', data_format)
                sheet.write(row, 3, employee.name, data_format)
                sheet.write(row, 4, employee.identification_id or '', data_format)
                sheet.write(row, 5, contract.date_start, date_format)
                sheet.write(row, 6, int(years_service), number_format)
                sheet.write(row, 7, f'{self.date_from.year}', data_format)
                sheet.write(row, 8, '', date_format)  # Fecha inicio vacaciones
                sheet.write(row, 9, '', date_format)  # Fecha fin vacaciones
                sheet.write(row, 10, 0, number_format)  # Días otorgados
                sheet.write(row, 11, 0, number_format)  # Días gozados
                sheet.write(row, 12, 0, number_format)  # Días pendientes
                sheet.write(row, 13, 0, number_format)  # Monto pago vacaciones
                sheet.write(row, 14, 'Sin vacaciones', data_format)
                sheet.write(row, 15, '', data_format)
                row += 1
            else:
                # Procesar cada período de vacaciones
                for leave in leaves:
                    # Calcular años de servicio al momento de las vacaciones
                    years_service = 0
                    if contract.date_start:
                        # leave.date_from puede ser datetime o date
                        if hasattr(leave.date_from, 'date'):
                            leave_date = leave.date_from.date()
                        else:
                            leave_date = leave.date_from
                        delta = leave_date - contract.date_start
                        years_service = delta.days / 365.25

                    # Calcular días de vacaciones
                    days_granted = leave.number_of_days or 0
                    days_used = leave.number_of_days_display or days_granted

                    # Calcular monto de pago de vacaciones (salario / 30 * días)
                    vacation_payment = 0
                    if contract.wage:
                        vacation_payment = (contract.wage / 30) * days_used

                    sheet.write(row, 0, self.company_id.company_registry or '', data_format)
                    sheet.write(row, 1, self.company_id.name, data_format)
                    sheet.write(row, 2, self.company_id.street or '', data_format)
                    sheet.write(row, 3, employee.name, data_format)
                    sheet.write(row, 4, employee.identification_id or '', data_format)
                    sheet.write(row, 5, contract.date_start, date_format)
                    sheet.write(row, 6, int(years_service), number_format)
                    # Obtener año de la fecha de inicio de vacaciones
                    if hasattr(leave.date_from, 'year'):
                        leave_year = leave.date_from.year
                    elif hasattr(leave.date_from, 'date'):
                        leave_year = leave.date_from.date().year
                    else:
                        leave_year = self.date_from.year  # Fallback
                    sheet.write(row, 7, f'{leave_year}', data_format)
                    sheet.write(row, 8, leave.date_from, date_format)
                    sheet.write(row, 9, leave.date_to, date_format)
                    sheet.write(row, 10, days_granted, number_format)
                    sheet.write(row, 11, days_used, number_format)
                    sheet.write(row, 12, max(0, days_granted - days_used), number_format)
                    sheet.write(row, 13, vacation_payment, number_format)
                    sheet.write(row, 14, 'Gozadas', data_format)
                    sheet.write(row, 15, leave.name or '', data_format)
                    row += 1

        workbook.close()
        output.seek(0)
        
        filename = f'MTESS_Libro_Vacaciones_{self.date_from}_{self.date_to}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'hr.payroll.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_dnit_salary_report(self):
        """Genera el Listado Nómina Salarial DNIT"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Listado Nómina DNIT')

        # Estilos
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})
        currency_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        # Encabezados del Listado Nómina Salarial DNIT
        headers = [

            'Ruc',

            'Dv',

            'Primer Apellido',

            'Segundo Apellido',

            'Primer Nombre',

            'Tipo de Pago',

            'Monto Bruto(Sin descuento)',

            'Descuento Jubilaci?n',

            'Descuento Seguro Social',

            'Otros Descuentos',

            'Monto Aguinaldo',

            'Correo Electr?nico',

            'Departamento',

            'Distrito',

            'Localidad/Barrio',

            'Direcci?n Completa',

            'Prefijo Linea Fija',

            'Linea Fija',

            'Prefijo Celular',

            'Celular',

            'Tipo de Empleado'

        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 16)

        # Obtener nóminas del período
        domain = [
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id)
        ]
        payslips = self.env['hr.payslip'].search(domain, order='employee_id, date_to')

        row = 1
        for slip in payslips:
            employee = slip.employee_id
            contract = slip.contract_id
            
            # Calcular valores usando el helper
            salario_base = self._get_salary_line_total(slip, 'BASIC') or contract.wage or 0
            bonificaciones = self._get_salary_line_total(slip, 'BONIFICACION_FAMILIAR')
            comisiones = 0  # TODO: Agregar si hay regla de comisiones
            horas_extras = self._get_salary_line_total(slip, 'HE_DIURNA') + self._get_salary_line_total(slip, 'HE_NOCTURNA')
            otros_ingresos = self._get_salary_line_total(slip, 'PY_ADICIONALES') - bonificaciones - horas_extras
            total_ingresos = self._get_salary_line_total(slip, 'PY_TOTAL_BRUTO') or salario_base + bonificaciones + comisiones + horas_extras + otros_ingresos
            
            ips_trabajador = abs(self._get_salary_line_total(slip, 'IPS_TRABAJADOR'))
            anticipos = 0  # TODO: Definir regla para anticipos
            otros_descuentos = abs(self._get_salary_line_total(slip, 'PY_DEDUCTION')) - ips_trabajador
            total_descuentos = ips_trabajador + anticipos + otros_descuentos
            neto = self._get_salary_line_total(slip, 'PY_NETO') or (total_ingresos - total_descuentos)
            aguinaldo = self._get_salary_line_total(slip, 'AGUINALDO')

            # Informaci?n bancaria

            forma_pago = ''

            if hasattr(employee, '_fields') and 'dnit_payment_type' in employee._fields:

                selection = dict(employee._fields['dnit_payment_type'].selection or [])

                forma_pago = selection.get(employee.dnit_payment_type, employee.dnit_payment_type or '')

            

            ruc = employee.dnit_ruc or ''

            dv = employee.dnit_dv or ''

            primer_apellido = employee.first_last_name or ''

            segundo_apellido = employee.second_last_name or ''

            primer_nombre = employee.first_name or ''

            prefijo_fijo = employee.dnit_phone_prefix or ''

            linea_fija = employee.dnit_phone_line or ''

            prefijo_cel = employee.dnit_mobile_prefix or ''

            celular = employee.dnit_mobile_line or ''

            email = employee.work_email or ''

            departamento = employee.dnit_department or ''

            distrito = employee.dnit_district or ''

            localidad = employee.dnit_locality or ''

            direccion = employee.dnit_address or ''

            tipo_empleado = employee.dnit_employee_type or ''

            descuento_jubilacion = 0  # TODO: Definir regla de jubilacion si aplica

            sheet.write(row, 0, ruc, data_format)
            sheet.write(row, 1, dv, data_format)
            sheet.write(row, 2, primer_apellido, data_format)
            sheet.write(row, 3, segundo_apellido, data_format)
            sheet.write(row, 4, primer_nombre, data_format)
            sheet.write(row, 5, forma_pago, data_format)
            sheet.write(row, 6, total_ingresos, currency_format)
            sheet.write(row, 7, descuento_jubilacion, currency_format)
            sheet.write(row, 8, ips_trabajador, currency_format)
            sheet.write(row, 9, otros_descuentos, currency_format)
            sheet.write(row, 10, aguinaldo, currency_format)
            sheet.write(row, 11, email, data_format)
            sheet.write(row, 12, departamento, data_format)
            sheet.write(row, 13, distrito, data_format)
            sheet.write(row, 14, localidad, data_format)
            sheet.write(row, 15, direccion, data_format)
            sheet.write(row, 16, prefijo_fijo, data_format)
            sheet.write(row, 17, linea_fija, data_format)
            sheet.write(row, 18, prefijo_cel, data_format)
            sheet.write(row, 19, celular, data_format)
            sheet.write(row, 20, tipo_empleado, data_format)
            row += 1

        workbook.close()
        output.seek(0)
        
        filename = f'DNIT_Listado_Nomina_{self.date_from}_{self.date_to}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'hr.payroll.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_payroll_summary_report(self):
        """Genera la Planilla de Salarios (Resumen por Conceptos)"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Planilla de Salarios')

        # Estilos
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#F2F2F2', 'border': 1, 'text_wrap': True, 'valign': 'vcenter'})
        data_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})

        # Titulo
        if self.payslip_run_id:
            titulo = self.payslip_run_id.name
        else:
            months = {
                1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
                5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
                9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
            }
            titulo = f"PLANILLA DE SALARIOS - {months[self.date_from.month]} {self.date_from.year}"

        sheet.write(0, 1, titulo, title_format)

        base_headers = [
            'Orden',
            'Funcionario',
            'Centro de Costo',
            'Dias Trab.',
            'Horas Ext.',
        ]
        concepts = self.env['hr.payroll.summary.concept'].search(
            [('active', '=', True)],
            order='sequence, id'
        )
        headers = base_headers + [concept.name for concept in concepts]

        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_format)
            sheet.set_column(col, col, 15)

        sheet.set_column(1, 1, 35)
        sheet.set_column(2, 2, 20)

        # Obtener nominas
        domain = [
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id)
        ]
        if self.payslip_run_id:
            domain.append(('payslip_run_id', '=', self.payslip_run_id.id))
        else:
            domain.extend([
                ('date_to', '>=', self.date_from),
                ('date_to', '<=', self.date_to)
            ])

        payslips = self.env['hr.payslip'].search(domain, order='employee_id')

        row = 3
        idx = 1
        for slip in payslips:
            employee = slip.employee_id
            contract = slip.contract_id

            dias_trab = sum(line.number_of_days for line in slip.worked_days_line_ids if line.code == 'WORK100')
            horas_ext = self._get_salary_line_total(slip, 'HE_DIURNA') + self._get_salary_line_total(slip, 'HE_NOCTURNA')

            centro_costo = ''
            if hasattr(contract, 'analytic_account_id') and contract.analytic_account_id:
                centro_costo = contract.analytic_account_id.name
            elif employee.department_id:
                centro_costo = employee.department_id.name

            sheet.write(row, 0, idx, data_format)
            sheet.write(row, 1, employee.name, data_format)
            sheet.write(row, 2, centro_costo, data_format)
            sheet.write(row, 3, dias_trab, number_format)
            sheet.write(row, 4, horas_ext, number_format)
            col = len(base_headers)
            for concept in concepts:
                value = self._get_payroll_summary_concept_value(slip, concept)
                sheet.write(row, col, value, number_format)
                col += 1

            idx += 1
            row += 1

        workbook.close()
        output.seek(0)

        filename = f'{titulo.replace(" ", "_")}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'hr.payroll.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
