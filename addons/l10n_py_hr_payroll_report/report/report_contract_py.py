from odoo import api, models
from datetime import datetime
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    relativedelta = None


class ReportContractPY(models.AbstractModel):
    _name = 'report.l10n_py_hr_payroll_report.report_contract_py'
    _description = 'Reporte de Contrato Laboral Paraguay'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Validar que haya docids
        if not docids:
            from odoo.exceptions import UserError
            raise UserError("No se seleccionó ningún contrato para imprimir. Por favor, abre un contrato y haz clic en 'Imprimir Contrato'.")
        
        # Usar sudo() para evitar problemas de permisos al acceder a estructuras salariales
        contracts = self.env['hr.contract'].sudo().browse(docids)
        
        # Filtrar solo contratos que existan
        contracts = contracts.filtered(lambda c: c.exists())
        
        if not contracts:
            from odoo.exceptions import UserError
            raise UserError("No se encontraron contratos válidos para imprimir.")
        
        # Calcular el HTML de cada contrato antes de pasarlo al template
        # Usar una lista de objetos tipo Bunch para que QWeb pueda acceder a los atributos
        from odoo.tools import Bunch
        contracts_with_html = []
        for contract in contracts:
            html_content = self._get_contract_html(contract)
            contracts_with_html.append(Bunch(
                contract=contract,
                html_content=html_content,
            ))
        
        return {
            'doc_ids': docids,
            'doc_model': 'hr.contract',
            'docs': contracts,
            'contracts_with_html': contracts_with_html,
            'data': data,
        }

    def _get_contract_html(self, contract):
        """Renderiza el contrato usando el contenido HTML del contrato o la plantilla"""
        try:
            # Priorizar el contenido HTML editable del contrato si existe
            # Si ya tiene contenido HTML, usarlo directamente sin procesar variables
            # (las variables ya fueron reemplazadas al seleccionar la plantilla)
            contract_html_content = getattr(contract, 'contract_html_content', False)
            if contract_html_content and contract_html_content.strip():
                # El HTML ya tiene las variables reemplazadas, usarlo directamente
                return contract_html_content.strip()
            
            # Si no hay contenido HTML en el contrato, buscar la plantilla y procesarla
            template = contract.contract_template_id
            
            if not template:
                # Si no hay plantilla seleccionada, usar la plantilla general por defecto
                template = self.env['hr.contract.template'].sudo().search([
                    ('active', '=', True),
                    ('template_code', '=', 'general')
                ], limit=1)
            
            if not template:
                # Si no hay plantilla general, usar la primera activa
                template = self.env['hr.contract.template'].sudo().search([
                    ('active', '=', True)
                ], limit=1)
            
            if not template:
                error_msg = (
                    "<div style='padding: 20px; border: 1px solid #ccc;'>"
                    "<h3>No hay plantilla de contrato disponible</h3>"
                    "<p>Por favor, selecciona una plantilla en el contrato o agrega contenido HTML directamente.</p>"
                    "<p><strong>Contrato:</strong> {}</p>"
                    "<p><strong>Empleado:</strong> {}</p>"
                    "</div>"
                ).format(
                    contract.name or 'Sin nombre',
                    contract.employee_id.name if contract.employee_id else 'Sin empleado'
                )
                return error_msg
            
            # Obtener el HTML de la descripción
            html_content = template.description or ""
            if not html_content or not html_content.strip():
                error_msg = (
                    "<div style='padding: 20px; border: 1px solid #ccc;'>"
                    "<h3>La plantilla de contrato está vacía</h3>"
                    "<p>La plantilla '{}' no tiene contenido. Por favor, edita la plantilla y agrega contenido.</p>"
                    "</div>"
                ).format(template.name or 'Sin nombre')
                return error_msg
            
            # Solo reemplazar variables si estamos usando la plantilla directamente
            # (no si ya tenemos contenido HTML procesado)
            html_content = self._replace_contract_variables(html_content, contract, template)
            
            if not html_content or not html_content.strip():
                return "<p>El contenido del contrato está vacío después de procesar las variables.</p>"
            
            return html_content.strip()
        except Exception as e:
            import traceback
            error_msg = (
                "<div style='padding: 20px; border: 1px solid red; background-color: #ffe6e6;'>"
                "<h3>Error al generar el contrato</h3>"
                "<p><strong>Error:</strong> {}</p>"
                "<pre style='background: white; padding: 10px; overflow: auto;'>{}</pre>"
                "</div>"
            ).format(str(e), traceback.format_exc())
            return error_msg

    def _replace_contract_variables(self, html, contract, template):
        """Reemplaza las variables de la plantilla con datos reales del contrato
        Soporta formatos: <<VARIABLE>> y {{ VARIABLE }}
        """
        employee = contract.employee_id
        company = contract.company_id
        job = contract.job_id
        
        # Preparar datos del contrato
        contract_date = contract.date_start or datetime.now()
        contract_city = company.city or company.state_id.name or "Asunción"
        contract_day = contract_date.day
        contract_month = self._get_month_name(contract_date.month)
        contract_year = contract_date.year
        
        # Datos de la empresa
        company_name = company.name or ""
        company_address = self._format_address(company)
        company_representative = company.partner_id.name or company_name
        company_representative_id = company.partner_id.vat or ""
        
        # Datos del empleado
        employee_name = employee.name or ""
        employee_nationality = employee.country_id.name or "Paraguaya"
        employee_id = employee.identification_id or ""
        employee_address = self._format_employee_address(employee)
        
        # Género y título del empleado
        if employee.gender == 'male':
            employee_title = 'el señor'
            employee_gender = 'masculino'
        elif employee.gender == 'female':
            employee_title = 'la señora'
            employee_gender = 'femenino'
        else:
            employee_title = ''
            employee_gender = ''
        
        # Edad del empleado
        if employee.birthday:
            today = datetime.now().date()
            age = today.year - employee.birthday.year - ((today.month, today.day) < (employee.birthday.month, employee.birthday.day))
            employee_age = 'mayor de edad' if age > 17 else 'menor de edad'
        else:
            employee_age = 'mayor de edad'
        
        # Datos del trabajo
        job_title = job.name if job else contract.name or ""
        work_location = company_address
        schedule_start = "08:00"
        schedule_end = "17:00"
        schedule_days = "lunes a viernes"
        schedule_breaks = "12:00 a 13:00"
        
        # Datos del salario
        if contract.currency_id and contract.currency_id.name == 'PYG':
            salary_amount = '{:,.0f}'.format(contract.wage).replace(',', '.') if contract.wage else "0"
        else:
            salary_amount = '{:,.2f}'.format(contract.wage) if contract.wage else "0"
        
        salary_amount_words = self._number_to_words(int(contract.wage)) if contract.wage else "cero"
        salary_currency_symbol = contract.currency_id.symbol if contract.currency_id else "Gs."
        salary_currency_unit = contract.currency_id.currency_unit_label if contract.currency_id else "guaraní"
        salary_payment_dates = "día 30 de cada mes"
        salary_bank = "Banco a definir"
        salary_notice_days = "15"
        
        # Herramientas (placeholders)
        tool_item_1 = "Equipos informáticos"
        tool_item_2 = "Material de oficina"
        tool_item_3 = "Otros insumos necesarios"
        tools_summary = f"{tool_item_1}, {tool_item_2}, {tool_item_3}"
        
        # Periodo de prueba
        if contract.date_start and relativedelta:
            trial_end_date_obj = datetime(contract_date.year, contract_date.month, contract_date.day)
            trial_end_date_obj += relativedelta(months=3)
            trial_end_date = trial_end_date_obj.strftime("%d de %s de %d" % (
                trial_end_date_obj.day,
                self._get_month_name(trial_end_date_obj.month),
                trial_end_date_obj.year
            ))
        else:
            trial_end_date = "fecha a definir"
        
        # Jurisdicción
        jurisdiction_city = contract_city
        
        # Obligaciones extra
        extra_obligation_1 = "Realizar las tareas asignadas con dedicación y esmero."
        extra_obligation_2 = "Mantener la confidencialidad de la información de la empresa."
        
        # Jornal diario (si aplica)
        daily_wage_amount = f"{contract.wage:,.0f}" if contract.wage else "0"
        daily_wage_words = self._number_to_words(int(contract.wage)) if contract.wage else "cero"
        
        # Comisión (si aplica)
        commission_amount = "0"
        commission_amount_words = "cero"
        commission_unit = "unidad"
        
        # Reemplazar todas las variables en el HTML
        replacements = {
            'contract_city': contract_city,
            'contract_day': str(contract_day),
            'contract_month': contract_month,
            'contract_year': str(contract_year),
            'company_name': company_name,
            'company_address': company_address,
            'company_representative': company_representative,
            'company_representative_id': company_representative_id,
            'employee_name': employee_name,
            'employee_nationality': employee_nationality,
            'employee_id': employee_id,
            'employee_address': employee_address,
            'job_title': job_title,
            'work_location': work_location,
            'schedule_start': schedule_start,
            'schedule_end': schedule_end,
            'schedule_days': schedule_days,
            'schedule_breaks': schedule_breaks,
            'salary_amount': salary_amount,
            'salary_amount_words': salary_amount_words,
            'salary_payment_dates': salary_payment_dates,
            'salary_bank': salary_bank,
            'salary_notice_days': salary_notice_days,
            'tool_item_1': tool_item_1,
            'tool_item_2': tool_item_2,
            'tool_item_3': tool_item_3,
            'tools_summary': tools_summary,
            'trial_end_date': trial_end_date,
            'jurisdiction_city': jurisdiction_city,
            'extra_obligation_1': extra_obligation_1,
            'extra_obligation_2': extra_obligation_2,
            'daily_wage_amount': daily_wage_amount,
            'daily_wage_words': daily_wage_words,
            'commission_amount': commission_amount,
            'commission_amount_words': commission_amount_words,
            'commission_unit': commission_unit,
        }
        
        # Agregar variables adicionales al diccionario (en mayúsculas)
        replacements.update({
            'NOMBRE_EMPLEADO': employee_name,
            'TITULO_EMPLEADO': employee_title,
            'GENERO_EMPLEADO': employee_gender,
            'EDAD_EMPLEADO': employee_age,
            'SIMBOLO_MONEDA': salary_currency_symbol,
            'UNIDAD_MONEDA': salary_currency_unit,
            'REGISTRO_PATRONAL': company.company_registry or '',
            'REGISTRO_PATRONAL_IPS': getattr(company, 'ips_registry_number', '') or '',
            # Agregar todas las variables en mayúsculas también
            'CONTRACT_CITY': contract_city,
            'CONTRACT_DAY': str(contract_day),
            'CONTRACT_MONTH': contract_month,
            'CONTRACT_YEAR': str(contract_year),
            'COMPANY_NAME': company_name,
            'COMPANY_ADDRESS': company_address,
            'COMPANY_REPRESENTATIVE': company_representative,
            'COMPANY_REPRESENTATIVE_ID': company_representative_id,
            'EMPLOYEE_NAME': employee_name,
            'EMPLOYEE_NATIONALITY': employee_nationality,
            'EMPLOYEE_ID': employee_id,
            'EMPLOYEE_ADDRESS': employee_address,
            'JOB_TITLE': job_title,
            'WORK_LOCATION': work_location,
            'SCHEDULE_START': schedule_start,
            'SCHEDULE_END': schedule_end,
            'SCHEDULE_DAYS': schedule_days,
            'SCHEDULE_BREAKS': schedule_breaks,
            'SALARY_AMOUNT': salary_amount,
            'SALARY_AMOUNT_WORDS': salary_amount_words,
            'SALARY_PAYMENT_DATES': salary_payment_dates,
            'SALARY_BANK': salary_bank,
            'SALARY_NOTICE_DAYS': salary_notice_days,
            'TOOL_ITEM_1': tool_item_1,
            'TOOL_ITEM_2': tool_item_2,
            'TOOL_ITEM_3': tool_item_3,
            'TOOLS_SUMMARY': tools_summary,
            'TRIAL_END_DATE': trial_end_date,
            'JURISDICTION_CITY': jurisdiction_city,
            'EXTRA_OBLIGATION_1': extra_obligation_1,
            'EXTRA_OBLIGATION_2': extra_obligation_2,
            'DAILY_WAGE_AMOUNT': daily_wage_amount,
            'DAILY_WAGE_WORDS': daily_wage_words,
            'COMMISSION_AMOUNT': commission_amount,
            'COMMISSION_AMOUNT_WORDS': commission_amount_words,
            'COMMISSION_UNIT': commission_unit,
        })
        
        # Reemplazar todas las variables con diferentes formatos
        for key, value in replacements.items():
            # Formato <<VARIABLE>>
            html = html.replace(f'<<{key.upper()}>>', str(value))
            html = html.replace(f'<<{key}>>', str(value))
            # Formato {{ VARIABLE }}
            html = html.replace(f'{{{{ {key} }}}}', str(value))
            html = html.replace(f'{{{{ {key.upper()} }}}}', str(value))
            # Formato sin espacios {{VARIABLE}}
            html = html.replace(f'{{{{{key}}}}}', str(value))
            html = html.replace(f'{{{{{key.upper()}}}}}', str(value))
        
        return html

    def _format_address(self, company):
        """Formatea la dirección de la empresa"""
        parts = []
        if company.street:
            parts.append(company.street)
        if company.street2:
            parts.append(company.street2)
        if company.city:
            parts.append(company.city)
        if company.state_id:
            parts.append(company.state_id.name)
        if company.country_id:
            parts.append(company.country_id.name)
        return ", ".join(parts) if parts else "Dirección no especificada"

    def _format_employee_address(self, employee):
        """Formatea la dirección del empleado"""
        if employee.address_home_id:
            return self._format_address(employee.address_home_id)
        return "Dirección no especificada"

    def _get_month_name(self, month_num):
        """Convierte número de mes a nombre en español"""
        months = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        return months.get(month_num, "")

    def _number_to_words(self, number):
        """Convierte número a palabras en español (versión básica)
        Para mejor funcionalidad, instalar: pip install num2words
        """
        try:
            from num2words import num2words
            return num2words(number, lang='es')
        except ImportError:
            # Versión básica sin librería externa
            if number == 0:
                return "cero"
            # Por ahora retornar el número como está si no hay num2words
            return str(number)

