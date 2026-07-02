# -*- coding: utf-8 -*-
"""
Wizard para crear datos de demostración de payslips.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class CreateDemoPayslipsWizard(models.TransientModel):
    _name = 'create.demo.payslips.wizard'
    _description = 'Crear Payslips de Demostración'

    def action_create_demo(self):
        """Crear payslips de demostración"""
        self.ensure_one()
        
        # Buscar empleados demo
        employee_30 = self.env.ref('l10n_py_hr_payroll_report.demo_employee_30_dias', raise_if_not_found=False)
        employee_24 = self.env.ref('l10n_py_hr_payroll_report.demo_employee_24_dias', raise_if_not_found=False)
        
        if not employee_30 or not employee_24:
            raise UserError(_("No se encontraron los empleados demo. Asegúrate de que los datos demo estén cargados."))
        
        # Obtener contratos
        contract_30 = employee_30.contract_ids.filtered(lambda c: c.state == 'open')
        contract_24 = employee_24.contract_ids.filtered(lambda c: c.state == 'open')
        
        if not contract_30 or not contract_24:
            raise UserError(_("No se encontraron contratos activos para los empleados demo."))
        
        # Obtener la estructura salarial paraguaya
        struct_py = self.env.ref(
            'l10n_py_hr_payroll_report.hr_payroll_structure_empleado_mensual_paraguay_1',
            raise_if_not_found=False,
        )
        if not struct_py:
            raise UserError(_("No se encontró la estructura salarial mensual. Asegúrate de que los datos están cargados."))
        
        # Asignar estructura salarial a los contratos si no la tienen
        if contract_30 and hasattr(contract_30[0], 'struct_id'):
            contract_30[0].struct_id = struct_py.id
        elif contract_30 and hasattr(contract_30[0], 'structure_type_id'):
            # En algunas versiones puede ser structure_type_id
            struct_type = struct_py.type_id
            if struct_type:
                contract_30[0].structure_type_id = struct_type.id
        
        if contract_24 and hasattr(contract_24[0], 'struct_id'):
            contract_24[0].struct_id = struct_py.id
        elif contract_24 and hasattr(contract_24[0], 'structure_type_id'):
            # En algunas versiones puede ser structure_type_id
            struct_type = struct_py.type_id
            if struct_type:
                contract_24[0].structure_type_id = struct_type.id
        
        # Fechas para el período (mes actual)
        today = datetime.now().date()
        date_from = today.replace(day=1)  # Primer día del mes
        # Último día del mes
        if today.month == 12:
            date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        # Crear lote de nómina
        payslip_run = self.env['hr.payslip.run'].create({
            'name': 'Demo - Nómina %s' % date_from.strftime('%B %Y'),
            'date_start': date_from,
            'date_end': date_to,
            'state': 'draft',
        })
        
        # Completar datos de empleados para los reportes
        self._complete_employee_data(employee_30, contract_30[0])
        self._complete_employee_data(employee_24, contract_24[0])
        
        # Completar datos de empresa
        self._complete_company_data()
        
        # Crear datos de vacaciones para pruebas
        self._create_demo_vacations(employee_30, employee_24)
        
        # Crear payslip para empleado 1 (30 días)
        struct_id = contract_30[0].struct_id.id if hasattr(contract_30[0], 'struct_id') and contract_30[0].struct_id else struct_py.id
        payslip_30 = self.env['hr.payslip'].create({
            'name': 'DEMO-001',
            'employee_id': employee_30.id,
            'contract_id': contract_30[0].id,
            'payslip_run_id': payslip_run.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': struct_id,
        })
        
        # Verificar que los parámetros de IPS existan (se crean automáticamente desde el XML)
        # Los valores se configuran desde la interfaz: Nómina → Configuración → Parámetros de regla
        # Si no están configurados, las reglas salariales usan valores por defecto (9.0% y 16.5%)
        param_ips_trabajador = self.env['hr.rule.parameter'].search([
            ('code', '=', 'ips_trabajador_py')
        ], limit=1)
        if not param_ips_trabajador:
            self.env['hr.rule.parameter'].create({
                'name': 'IPS Trabajador (%)',
                'code': 'ips_trabajador_py',
            })
        
        param_ips_patronal = self.env['hr.rule.parameter'].search([
            ('code', '=', 'ips_patronal_py')
        ], limit=1)
        if not param_ips_patronal:
            self.env['hr.rule.parameter'].create({
                'name': 'IPS Patronal (%)',
                'code': 'ips_patronal_py',
            })
        
        # Obtener tipo de entrada de trabajo por defecto (días trabajados normales)
        work_entry_type = self.env['hr.work.entry.type'].search([
            ('code', '=', 'WORK100')
        ], limit=1)
        if not work_entry_type:
            # Si no existe por código, buscar uno genérico de trabajo
            work_entry_type = self.env['hr.work.entry.type'].search([
                ('code', 'in', ['WORK100', 'WORK', 'WORK1'])
            ], limit=1)
        if not work_entry_type:
            # Si aún no existe, buscar cualquier tipo de trabajo (no vacaciones, no licencia)
            work_entry_type = self.env['hr.work.entry.type'].search([
                ('is_leave', '=', False)
            ], limit=1)
        
        # Crear líneas de días trabajados y horas extras (30 días)
        if work_entry_type:
            self.env['hr.payslip.worked_days'].create({
                'payslip_id': payslip_30.id,
                'work_entry_type_id': work_entry_type.id,
                'code': 'WORK100',
                'name': 'Días trabajados',
                'number_of_days': 30.0,
                'number_of_hours': 240.0,  # 30 días * 8 horas
            })
            
            # Crear horas extras diurnas para pruebas
            he_type = self.env['hr.work.entry.type'].search([
                ('code', '=', 'HE_DIURNA')
            ], limit=1)
            if not he_type:
                he_type = self.env['hr.work.entry.type'].search([
                    ('name', 'ilike', 'extra')
                ], limit=1)
            
            if he_type:
                self.env['hr.payslip.worked_days'].create({
                    'payslip_id': payslip_30.id,
                    'work_entry_type_id': he_type.id,
                    'code': 'HE_DIURNA',
                    'name': 'Horas Extras Diurnas',
                    'number_of_days': 2.0,
                    'number_of_hours': 16.0,  # 2 días * 8 horas
                })
        else:
            raise UserError(_("No se encontró un tipo de entrada de trabajo. Configura los tipos de entrada de trabajo en Recursos Humanos → Configuración → Tipos de Entrada de Trabajo."))
        
        # Crear payslip para empleado 2 (24 días)
        struct_id_24 = contract_24[0].struct_id.id if hasattr(contract_24[0], 'struct_id') and contract_24[0].struct_id else struct_py.id
        payslip_24 = self.env['hr.payslip'].create({
            'name': 'DEMO-002',
            'employee_id': employee_24.id,
            'contract_id': contract_24[0].id,
            'payslip_run_id': payslip_run.id,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': struct_id_24,
        })
        
        # Crear línea de días trabajados (24 días)
        if work_entry_type:
            self.env['hr.payslip.worked_days'].create({
                'payslip_id': payslip_24.id,
                'work_entry_type_id': work_entry_type.id,
                'code': 'WORK100',
                'name': 'Días trabajados',
                'number_of_days': 24.0,
                'number_of_hours': 192.0,  # 24 días * 8 horas
            })
            
            # Crear horas extras nocturnas para pruebas
            he_noct_type = self.env['hr.work.entry.type'].search([
                ('code', '=', 'HE_NOCTURNA')
            ], limit=1)
            if not he_noct_type:
                he_noct_type = self.env['hr.work.entry.type'].search([
                    ('name', 'ilike', 'nocturna')
                ], limit=1)
            
            if he_noct_type:
                self.env['hr.payslip.worked_days'].create({
                    'payslip_id': payslip_24.id,
                    'work_entry_type_id': he_noct_type.id,
                    'code': 'HE_NOCTURNA',
                    'name': 'Horas Extras Nocturnas',
                    'number_of_days': 1.0,
                    'number_of_hours': 8.0,
                })
        else:
            raise UserError(_("No se encontró un tipo de entrada de trabajo. Configura los tipos de entrada de trabajo en Recursos Humanos → Configuración → Tipos de Entrada de Trabajo."))
        
        # Calcular los payslips (esto calculará todas las líneas incluyendo IPS)
        try:
            payslip_30.compute_sheet()
            payslip_24.compute_sheet()
        except Exception as e:
            raise UserError(_("Error al calcular los payslips: %s") % str(e))
        
        # Verificar que se calcularon las líneas de IPS
        ips_30 = payslip_30.line_ids.filtered(lambda l: l.code == 'IPS_TRABAJADOR')
        ips_24 = payslip_24.line_ids.filtered(lambda l: l.code == 'IPS_TRABAJADOR')
        
        if not ips_30:
            raise UserError(_("No se calculó la línea de IPS para el empleado 1. Verifica que la estructura salarial tenga la regla IPS_TRABAJADOR."))
        if not ips_24:
            raise UserError(_("No se calculó la línea de IPS para el empleado 2. Verifica que la estructura salarial tenga la regla IPS_TRABAJADOR."))
        
        # Confirmar y procesar
        try:
            payslip_30.action_payslip_done()
            payslip_24.action_payslip_done()
            
            payslip_run.action_validate()
        except Exception as e:
            raise UserError(_("Error al confirmar los payslips: %s") % str(e))
        
        # Preparar mensaje de éxito con detalles
        total_ips_30 = abs(ips_30[0].total) if ips_30 else 0.0
        total_ips_24 = abs(ips_24[0].total) if ips_24 else 0.0
        total_bruto_30 = payslip_30.get_total_ingresos() or 0.0
        total_bruto_24 = payslip_24.get_total_ingresos() or 0.0
        total_neto_30 = payslip_30.get_total_cobrar() or 0.0
        total_neto_24 = payslip_24.get_total_cobrar() or 0.0
        
        # Mostrar notificación de éxito
        message = _("""
Lote de nómina demo creado exitosamente:

Lote: %s
Período: %s al %s

Empleado 1 - %s (30 días):
  - Salario bruto: %s Gs.
  - IPS trabajador (9%%): %s Gs.
  - Neto a pagar: %s Gs.

Empleado 2 - %s (24 días):
  - Salario bruto: %s Gs.
  - IPS trabajador (9%%): %s Gs.
  - Neto a pagar: %s Gs.

Datos adicionales creados:
  ✓ Información completa de empleados (género, estado civil, fecha nacimiento, nacionalidad, cargo)
  ✓ Direcciones completas de empleados y empresa
  ✓ Cuentas bancarias con datos de banco
  ✓ Calendarios de trabajo asignados
  ✓ Registros de vacaciones para pruebas de reportes MTESS
  ✓ Horas extras en los payslips

El lote está en estado 'Hecho' y listo para:
  - Generar reportes PDF (Recibos y Planilla IPS)
  - Exportar Planilla IPS a Excel
  - Exportar pagos bancarios
  - Generar reportes MTESS (Planilla Mensual, Libro Empleados, Libro Vacaciones)
  - Generar reporte DNIT (Listado Nómina Salarial)
        """) % (
            payslip_run.name,
            date_from.strftime('%d/%m/%Y'),
            date_to.strftime('%d/%m/%Y'),
            employee_30.name,
            '{:,.0f}'.format(total_bruto_30),
            '{:,.0f}'.format(total_ips_30),
            '{:,.0f}'.format(total_neto_30),
            employee_24.name,
            '{:,.0f}'.format(total_bruto_24),
            '{:,.0f}'.format(total_ips_24),
            '{:,.0f}'.format(total_neto_24),
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lote de Nómina Demo Creado - %s') % payslip_run.name,
            'res_model': 'hr.payslip.run',
            'res_id': payslip_run.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_id': payslip_run.id},
        }

    def _complete_employee_data(self, employee, contract):
        """Completar datos del empleado para los reportes"""
        # Obtener o crear partner del empleado
        partner = getattr(employee, 'address_home_id', False) or getattr(employee, 'work_contact_id', False)
        if not partner:
            # Crear partner si no existe
            partner = self.env['res.partner'].create({
                'name': employee.name,
                'is_company': False,
            })
            employee.address_home_id = partner.id
        
        # Completar datos del partner (dirección)
        if not partner.street:
            partner.write({
                'street': 'Av. Mariscal López 1234',
                'street2': 'Barrio Centro',
                'city': 'Asunción',
                'zip': '1000',
            })
            # Asignar país Paraguay si existe
            country_py = self.env['res.country'].search([('code', '=', 'PY')], limit=1)
            if country_py:
                partner.country_id = country_py.id
        
        # Completar datos del empleado
        employee_vals = {}
        
        # Género
        if not employee.gender:
            employee_vals['gender'] = 'male' if 'Juan' in employee.name else 'female'
        
        # Estado civil
        if not employee.marital:
            employee_vals['marital'] = 'married'
        
        # Fecha de nacimiento
        if not employee.birthday:
            from dateutil.relativedelta import relativedelta
            employee_vals['birthday'] = datetime.now().date() - relativedelta(years=30)
        
        # Nacionalidad
        if not employee.country_id:
            country_py = self.env['res.country'].search([('code', '=', 'PY')], limit=1)
            if country_py:
                employee_vals['country_id'] = country_py.id
        
        # Cargo/Profesión
        if not employee.job_title:
            employee_vals['job_title'] = 'Analista' if 'Juan' in employee.name else 'Asistente'
        
        # Actualizar empleado
        if employee_vals:
            employee.write(employee_vals)
        
        # Crear o actualizar cuenta bancaria
        bank_account = employee.bank_account_id
        if not bank_account:
            # Buscar banco demo o crear uno
            bank = self.env['res.bank'].search([('name', 'ilike', 'banco')], limit=1)
            if not bank:
                bank = self.env['res.bank'].create({
                    'name': 'Banco Nacional de Fomento',
                    'bic': 'BNFOPYPY',
                })
            
            # Número de cuenta único por empleado
            acc_number = '1234567890123456' if 'Juan' in employee.name else '9876543210987654'
            
            # Verificar si ya existe una cuenta bancaria con ese número para ese partner
            existing_account = self.env['res.partner.bank'].search([
                ('acc_number', '=', acc_number),
                ('partner_id', '=', partner.id)
            ], limit=1)
            
            if existing_account:
                # Usar la cuenta existente
                bank_account = existing_account
            else:
                # Crear nueva cuenta bancaria solo si no existe
                bank_account = self.env['res.partner.bank'].create({
                    'acc_number': acc_number,
                    'partner_id': partner.id,
                    'bank_id': bank.id,
                })
            
            # Asignar la cuenta bancaria al empleado (usar write para evitar problemas de estado)
            try:
                employee.write({'bank_account_id': bank_account.id})
            except:
                # Si no se puede asignar directamente, intentar asignar al partner
                if hasattr(employee, 'address_home_id') and employee.address_home_id:
                    employee.address_home_id.bank_ids = [(4, bank_account.id)]
        
        # Completar datos del contrato
        contract_vals = {}
        
        # Tipo de salario
        if not hasattr(contract, 'wage_type') or not contract.wage_type:
            # Intentar establecer wage_type si existe el campo
            try:
                contract.wage_type = 'monthly'
            except:
                pass
        
        # Calendario de trabajo
        if not contract.resource_calendar_id:
            calendar = self.env['resource.calendar'].search([
                ('name', 'ilike', '40 horas')
            ], limit=1)
            if not calendar:
                # Crear calendario básico
                calendar = self.env['resource.calendar'].create({
                    'name': 'Jornada 40 horas semanales',
                    'hours_per_day': 8.0,
                    'hours_per_week': 40.0,
                })
            # Usar write para evitar problemas de estado
            try:
                contract.write({'resource_calendar_id': calendar.id})
            except:
                # Si el contrato está en un estado que no permite modificaciones, continuar
                pass

    def _complete_company_data(self):
        """Completar datos de la empresa para los reportes"""
        company = self.env.company
        
        company_vals = {}
        
        # N° Patronal
        if not company.company_registry:
            company_vals['company_registry'] = '123456-7'
        
        # RUC
        if not company.vat:
            company_vals['vat'] = '80012345-7'
        
        # Dirección
        if not company.street:
            company_vals['street'] = 'Av. España 1234'
            company_vals['street2'] = 'Edificio Empresarial'
            company_vals['city'] = 'Asunción'
            company_vals['zip'] = '1000'
        
        # Teléfono
        if not company.phone:
            company_vals['phone'] = '+595 21 123456'
        
        # País
        if not company.country_id:
            country_py = self.env['res.country'].search([('code', '=', 'PY')], limit=1)
            if country_py:
                company_vals['country_id'] = country_py.id
        
        # Actualizar empresa
        if company_vals:
            company.write(company_vals)
        
        # Representante legal (partner de la empresa)
        if company.partner_id:
            if not company.partner_id.vat:
                company.partner_id.vat = company_vals.get('vat', '80012345-7')

    def _create_demo_vacations(self, employee_30, employee_24):
        """Crear registros de vacaciones de ejemplo para pruebas"""
        # Buscar tipo de vacaciones
        leave_type = self.env['hr.leave.type'].search([
            ('name', 'ilike', 'vacaciones')
        ], limit=1)
        
        if not leave_type:
            # Crear tipo de vacaciones si no existe
            # En Odoo 18, los campos pueden variar, usar solo los campos básicos
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Vacaciones Anuales',
            })
        
        # Crear asignaciones de vacaciones para ambos empleados primero
        # Crear con más días de los que se van a usar para asegurar que haya disponibilidad
        allocation_30 = self._create_leave_allocation(employee_30, leave_type, 30.0)  # 30 días de asignación
        allocation_24 = self._create_leave_allocation(employee_24, leave_type, 30.0)  # 30 días de asignación
        
        # Verificar que las asignaciones estén validadas antes de continuar
        # Si no se pueden crear/validar, simplemente no crear las solicitudes de vacaciones
        if not allocation_30 or allocation_30.state != 'validate':
            # Si no se puede crear la asignación, continuar sin crear vacaciones para este empleado
            _logger.warning("No se pudo crear/validar asignación de vacaciones para %s. Se omitirán las solicitudes de vacaciones." % employee_30.name)
            allocation_30 = None
        if not allocation_24 or allocation_24.state != 'validate':
            _logger.warning("No se pudo crear/validar asignación de vacaciones para %s. Se omitirán las solicitudes de vacaciones." % employee_24.name)
            allocation_24 = None
        
        # Crear vacaciones para empleado 1 (hace 2 meses)
        today = datetime.now().date()
        date_from_vac = today - relativedelta(months=2, days=1)
        date_to_vac = date_from_vac + relativedelta(days=10)
        
        # Verificar que no exista ya una solicitud de vacaciones en ese período
        existing_leave = self.env['hr.leave'].search([
            ('employee_id', '=', employee_30.id),
            ('date_from', '<=', date_to_vac),
            ('date_to', '>=', date_from_vac),
        ], limit=1)
        
        # Solo crear solicitud si hay una asignación válida
        if not existing_leave and allocation_30:
            # Crear solicitud de vacaciones primero en estado draft
            leave = self.env['hr.leave'].sudo().create({
                'name': 'Vacaciones Anuales',
                'employee_id': employee_30.id,
                'holiday_status_id': leave_type.id,
                'date_from': datetime.combine(date_from_vac, datetime.min.time()),
                'date_to': datetime.combine(date_to_vac, datetime.max.time()),
                'request_date_from': date_from_vac,
                'request_date_to': date_to_vac,
                'number_of_days': 10.0,
            })
            # Validar la solicitud si es posible
            try:
                if hasattr(leave, 'action_approve'):
                    leave.action_approve()
                if hasattr(leave, 'action_validate'):
                    leave.action_validate()
                else:
                    # Si no hay métodos de validación, intentar cambiar el estado directamente
                    leave.write({'state': 'validate'})
            except:
                # Si no se puede validar, dejar en el estado que tenga
                pass
        
        # Crear vacaciones para empleado 2 (hace 1 mes)
        date_from_vac2 = today - relativedelta(months=1, days=5)
        date_to_vac2 = date_from_vac2 + relativedelta(days=7)
        
        existing_leave2 = self.env['hr.leave'].search([
            ('employee_id', '=', employee_24.id),
            ('date_from', '<=', date_to_vac2),
            ('date_to', '>=', date_from_vac2),
        ], limit=1)
        
        # Solo crear solicitud si hay una asignación válida
        if not existing_leave2 and allocation_24:
            # Crear solicitud de vacaciones primero en estado draft
            leave2 = self.env['hr.leave'].sudo().create({
                'name': 'Vacaciones Anuales',
                'employee_id': employee_24.id,
                'holiday_status_id': leave_type.id,
                'date_from': datetime.combine(date_from_vac2, datetime.min.time()),
                'date_to': datetime.combine(date_to_vac2, datetime.max.time()),
                'request_date_from': date_from_vac2,
                'request_date_to': date_to_vac2,
                'number_of_days': 7.0,
            })
            # Validar la solicitud si es posible
            try:
                if hasattr(leave2, 'action_approve'):
                    leave2.action_approve()
                if hasattr(leave2, 'action_validate'):
                    leave2.action_validate()
                else:
                    # Si no hay métodos de validación, intentar cambiar el estado directamente
                    leave2.write({'state': 'validate'})
            except:
                # Si no se puede validar, dejar en el estado que tenga
                pass

    def _create_leave_allocation(self, employee, leave_type, number_of_days):
        """Crear asignación de vacaciones para un empleado"""
        # Verificar si ya existe una asignación válida para este empleado y tipo
        existing_allocation = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee.id),
            ('holiday_status_id', '=', leave_type.id),
            ('state', '=', 'validate'),
        ], limit=1)
        
        if existing_allocation:
            # Si existe, verificar que tenga suficientes días disponibles
            # Si no tiene suficientes, aumentar los días
            if existing_allocation.number_of_days < number_of_days:
                try:
                    existing_allocation.write({'number_of_days': number_of_days})
                except:
                    pass
            return existing_allocation
        
        # Crear asignación de vacaciones con solo los campos básicos que existen en Odoo 18
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Asignación de Vacaciones - %s' % employee.name,
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': number_of_days,
        })
        
        # Validar la asignación usando sudo para tener permisos de administrador
        try:
            allocation_sudo = allocation.sudo()
            # Intentar validar usando los métodos estándar
            if hasattr(allocation_sudo, 'action_approve'):
                allocation_sudo.action_approve()
            if hasattr(allocation_sudo, 'action_validate'):
                allocation_sudo.action_validate()
            else:
                # Si no hay métodos, intentar cambiar el estado directamente
                allocation_sudo.write({'state': 'validate'})
            
            # Refrescar para obtener el estado actualizado
            allocation.invalidate_recordset(['state'])
            allocation.refresh()
            
            # Si aún no está validada, intentar forzar el estado
            if allocation.state != 'validate':
                allocation_sudo.write({'state': 'validate'})
        except Exception as e:
            # Si falla la validación, intentar crear una nueva asignación con estado validate directamente
            try:
                allocation.unlink()
                allocation = self.env['hr.leave.allocation'].sudo().create({
                    'name': 'Asignación de Vacaciones - %s' % employee.name,
                    'employee_id': employee.id,
                    'holiday_status_id': leave_type.id,
                    'number_of_days': number_of_days,
                    'state': 'validate',
                })
            except:
                # Si aún falla, continuar sin asignación (la solicitud fallará pero no romperá el wizard)
                pass
        
        return allocation
