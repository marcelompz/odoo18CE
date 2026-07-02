# -*- coding: utf-8 -*-

from odoo import models, api, fields
from datetime import datetime


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_report_payslip_funcionario(self):
        """Abrir el reporte de recibo de pago de funcionario"""
        self.ensure_one()
        return self.env.ref('l10n_py_hr_payroll_report.action_report_payslip_funcionario').report_action(self)

    def action_report_payslip_ips(self):
        """Abrir el reporte de planilla IPS (permite múltiples payslips)"""
        # No usar ensure_one() porque permite generar planilla para múltiples empleados
        return self.env.ref('l10n_py_hr_payroll_report.action_report_payslip_ips').report_action(self)

    def get_worked_hours(self):
        """Calcular horas trabajadas en el período"""
        self.ensure_one()
        if self.contract_id and self.contract_id.resource_calendar_id:
            # Calcular días hábiles en el período
            from_date = self.date_from
            to_date = self.date_to
            calendar = self.contract_id.resource_calendar_id
            hours_per_day = calendar.hours_per_day
            # Calcular días trabajados (aproximado)
            days_worked = self.get_worked_days()
            return int(days_worked * hours_per_day) if days_worked and hours_per_day else 0
        # Si no hay calendario, calcular base estándar: 30 días * 6 horas = 180 horas
        days = self.get_worked_days()
        return int(days * 6) if days else 0

    def get_worked_days(self):
        """Calcular días trabajados en el período"""
        self.ensure_one()
        # Buscar línea de días trabajados en el payslip
        worked_days_lines = self.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100' or 'WORK' in (l.code or ''))
        if worked_days_lines:
            total_days = sum(worked_days_lines.mapped('number_of_days'))
            return int(total_days) if total_days else 0
        # Si no hay registro, calcular días entre fechas (aproximado)
        if self.date_from and self.date_to:
            delta = (self.date_to - self.date_from).days + 1
            return delta
        return 0

    def get_payment_method(self):
        """Obtener método de pago"""
        self.ensure_one()
        # Verificar si hay información en la cuenta bancaria del empleado
        if self.employee_id.bank_account_id:
            return 'Banco'
        # Verificar si el contrato tiene información de pago
        if self.contract_id:
            # Si el contrato tiene información de cuenta bancaria o salario
            return 'Banco'  # Valor por defecto para contratos
        return 'Efectivo'

    def get_employee_category(self):
        """Obtener categoría del empleado (Mensualero u Obrero)"""
        self.ensure_one()
        if self.contract_id:
            # Verificar si tiene el campo employee_type y su valor
            employee_type = getattr(self.contract_id, 'employee_type', None)
            if employee_type == 'employee':
                return 'Mensualero'
        return 'Obrero'

    def _get_report_url(self, report_ref):
        """Generar URL de acceso al PDF del reporte"""
        self.ensure_one()
        report_action = self.env.ref(report_ref, raise_if_not_found=False)
        if not report_action:
            return False
        
        # Generar URL completa con la URL base del sistema
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        # Obtener el token de acceso si existe (hr.payslip puede tener este campo en Odoo 18)
        access_token = getattr(self, 'access_token', None)
        
        # Construir la URL del PDF del reporte
        pdf_url = '%s/report/pdf/%s/%s' % (base_url, report_action.report_name, self.id)
        if access_token:
            pdf_url = '%s?access_token=%s' % (pdf_url, access_token)
        
        return pdf_url

    @property
    def access_url(self):
        """URL de acceso público al PDF del reporte"""
        self.ensure_one()
        return self._get_report_url('l10n_py_hr_payroll_report.action_report_payslip_funcionario')

    def get_qr_code_value(self):
        """Generar valor del código QR para validación del Ministerio de Trabajo"""
        self.ensure_one()
        # Información básica para el QR
        # Python 3 maneja UTF-8 por defecto en strings
        qr_data = {
            'empresa': str(self.company_id.name or ''),
            'ruc': str(self.company_id.vat or ''),
            'trabajador': str(self.employee_id.name or ''),
            'ci': str(self.employee_id.identification_id or ''),
            'periodo': '{} al {}'.format(
                self.date_from.strftime('%d/%m/%Y') if self.date_from else '',
                self.date_to.strftime('%d/%m/%Y') if self.date_to else ''
            ),
            'numero': str(self.number or self.id),
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Generar string para el QR (formato separado por pipes)
        # Nota: El formato exacto debe ser verificado con el Ministerio de Trabajo de Paraguay
        # El QR puede contener una URL del Ministerio de Trabajo para validación
        # Por ahora generamos un QR con los datos del documento para validación interna
        qr_string = "{}|{}|{}|{}|{}|{}".format(
            qr_data['ruc'],
            qr_data['ci'],
            qr_data['numero'],
            qr_data['periodo'],
            qr_data['empresa'],
            qr_data['fecha']
        )
        
        return qr_string

    # -------------------------------------------------------------------------
    # Totales basados en la estructura salarial PY
    # -------------------------------------------------------------------------

    def _get_line_total_by_code(self, codes):
        """Helper para obtener totales de líneas específicas."""
        self.ensure_one()
        if isinstance(codes, str):
            codes = {codes}
        lines = self.line_ids.filtered(lambda l: l.code in codes)
        return sum(lines.mapped('total')) if lines else 0.0

    def get_total_ingresos(self):
        """Obtener total de ingresos siguiendo la estructura paraguaya."""
        self.ensure_one()
        # Priorizar la regla TOTAL_SALARIOS si existe
        total = self._get_line_total_by_code({'TOTAL_SALARIOS'})
        if total:
            return total

        # Como fallback sumar categorías de ingresos
        income_categories = {'PY_INGRESOS_BASICOS', 'PY_ADICIONALES', 'PY_TOTAL_BRUTO', 'BASIC', 'ALW'}
        ingresos_lines = self.line_ids.filtered(
            lambda l: l.appears_on_payslip and l.total > 0 and l.category_id and l.category_id.code in income_categories
        )
        return sum(ingresos_lines.mapped('total'))

    def get_total_egresos(self):
        """Obtener total de deducciones siguiendo la estructura paraguaya."""
        self.ensure_one()
        total = abs(self._get_line_total_by_code({'TOTAL_DEDUCCIONES'}))
        if total:
            return total

        deduction_categories = {'PY_DEDUCTION', 'DED'}
        egresos_lines = self.line_ids.filtered(
            lambda l: l.appears_on_payslip and l.total < 0 and l.category_id and l.category_id.code in deduction_categories
        )
        return abs(sum(egresos_lines.mapped('total')))

    def get_total_cobrar(self):
        """Obtener total a cobrar basado en NET / categoría PY_NETO."""
        self.ensure_one()
        net_line = self.line_ids.filtered(lambda l: l.code == 'NET' or (l.category_id and l.category_id.code == 'PY_NETO'))
        if net_line:
            return net_line[0].total
        return self.get_total_ingresos() - self.get_total_egresos()

    def get_ips_trabajador(self):
        """Obtener monto de IPS descontado al trabajador (9%)."""
        self.ensure_one()
        ips_line = self.line_ids.filtered(lambda l: l.code == 'IPS_TRABAJADOR')
        if ips_line:
            # El valor viene negativo (es deducción), así que lo convertimos a positivo
            return abs(sum(ips_line.mapped('total')))
        return 0.0

    def get_payslip_lines_for_report(self):
        """Obtener líneas del payslip filtradas para el reporte.
        Filtra líneas con valor cero, evita duplicados priorizando reglas paraguayas,
        y excluye líneas de totales que no deben aparecer en el recibo individual.
        """
        self.ensure_one()
        
        # Códigos de líneas de totales que NO deben aparecer en el recibo (solo se usan para cálculo)
        total_codes_to_exclude = {
            'TOTAL_SALARIOS', 'TOTAL_DEDUCCIONES', 'NET', 
            'SUELDO_IMPO', 'SUELDO_IMPOYABLE', 'BASE_IMPOYABLE', 'BASE',
            'BASIC'  # Regla estándar de Odoo que duplica SALARIO_BASE
        }
        
        # Categorías de totales que NO deben aparecer como líneas individuales
        total_categories_to_exclude = {'PY_TOTAL_BRUTO', 'PY_NETO', 'NET', 'PY_EMPLOYER', 'PY_PROVISION'}
        
        # Categorías estándar que no deben aparecer si ya existe una versión paraguaya
        standard_categories_to_exclude_if_py_exists = {'BASIC', 'ALW'}
        
        # Filtrar solo líneas que aparecen en el recibo y tienen valor diferente de cero
        # Excluir líneas de totales y cargas patronales
        lines = self.line_ids.filtered(lambda l: 
            l.appears_on_payslip 
            and l.total != 0 
            and (not l.code or l.code not in total_codes_to_exclude)
            and (not l.category_id or not l.category_id.code or l.category_id.code not in total_categories_to_exclude)
        )
        
        # Evitar duplicados: si hay dos líneas con mismo código, mantener solo la paraguaya
        # También evitar reglas estándar (BASIC, ALW) si existe una versión paraguaya
        seen_codes = {}
        seen_py_categories = set()
        filtered_lines = self.env['hr.payslip.line']
        
        for line in lines.sorted(lambda l: l.sequence):
            # Excluir cargas patronales y provisiones (no aparecen en recibo del trabajador)
            if line.category_id and line.category_id.code:
                if line.category_id.code in {'PY_EMPLOYER', 'PY_PROVISION', 'EMPLOYER', 'PROVISION'}:
                    continue
                # Excluir reglas estándar (BASIC, ALW) si ya existe una versión paraguaya equivalente
                if line.category_id.code in standard_categories_to_exclude_if_py_exists:
                    py_category = 'PY_' + line.category_id.code
                    if py_category in seen_py_categories:
                        continue
            
            # Si no tiene código, verificar si la categoría es válida antes de incluir
            if not line.code:
                # Solo incluir si no es una categoría de totales o cargas patronales
                if line.category_id and line.category_id.code:
                    if line.category_id.code in total_categories_to_exclude:
                        continue
                    # Marcar categorías paraguayas vistas
                    if line.category_id.code.startswith('PY_'):
                        seen_py_categories.add(line.category_id.code)
                filtered_lines |= line
                continue
            
            # Si el código no se ha visto, incluir
            if line.code not in seen_codes:
                seen_codes[line.code] = line
                # Marcar categoría paraguaya si existe
                if line.category_id and line.category_id.code and line.category_id.code.startswith('PY_'):
                    seen_py_categories.add(line.category_id.code)
                filtered_lines |= line
            else:
                # Si ya existe, verificar si la nueva es paraguaya (PY_*)
                existing_line = seen_codes[line.code]
                existing_is_py = existing_line.category_id and existing_line.category_id.code and existing_line.category_id.code.startswith('PY_')
                current_is_py = line.category_id and line.category_id.code and line.category_id.code.startswith('PY_')
                
                # Si la nueva es paraguaya y la existente no, reemplazar
                if current_is_py and not existing_is_py:
                    filtered_lines -= existing_line
                    filtered_lines |= line
                    seen_codes[line.code] = line
                    seen_py_categories.add(line.category_id.code)
        
        return filtered_lines


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_generate_payroll_summary(self):
        """Generar Planilla de Salarios directamente desde el lote"""
        self.ensure_one()
        wizard = self.env['hr.payroll.report.wizard'].create({
            'report_type': 'payroll_summary',
            'payslip_run_id': self.id,
            'date_from': self.date_start,
            'date_to': self.date_end,
            'company_id': self.company_id.id,
        })
        return wizard.action_generate_xlsx()
