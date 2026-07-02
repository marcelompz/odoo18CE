# -*- coding: utf-8 -*-
"""
Script para crear datos de demostración de payslips con diferentes días trabajados.
Este script debe ejecutarse manualmente desde la consola de Odoo o como método de un wizard.
"""

from odoo import api, models
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def create_demo_payslips(env):
    """
    Crear payslips de demostración con diferentes días trabajados.
    
    Args:
        env: Environment de Odoo
    """
    # Buscar empleados demo
    employee_30 = env.ref('l10n_py_hr_payroll_report.demo_employee_30_dias', raise_if_not_found=False)
    employee_24 = env.ref('l10n_py_hr_payroll_report.demo_employee_24_dias', raise_if_not_found=False)
    
    if not employee_30 or not employee_24:
        return "No se encontraron los empleados demo. Asegúrate de que los datos demo estén cargados."
    
    # Obtener contratos
    contract_30 = employee_30.contract_ids.filtered(lambda c: c.state == 'open')
    contract_24 = employee_24.contract_ids.filtered(lambda c: c.state == 'open')
    
    if not contract_30 or not contract_24:
        return "No se encontraron contratos activos para los empleados demo."
    
    # Fechas para el período (mes actual)
    today = datetime.now().date()
    date_from = today.replace(day=1)  # Primer día del mes
    # Último día del mes
    if today.month == 12:
        date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # Crear lote de nómina
    payslip_run = env['hr.payslip.run'].create({
        'name': 'Demo - Nómina %s' % date_from.strftime('%B %Y'),
        'date_start': date_from,
        'date_end': date_to,
        'state': 'draft',
    })
    
    # Crear payslip para empleado 1 (30 días)
    payslip_30 = env['hr.payslip'].create({
        'name': 'DEMO-001',
        'employee_id': employee_30.id,
        'contract_id': contract_30[0].id,
        'payslip_run_id': payslip_run.id,
        'date_from': date_from,
        'date_to': date_to,
        'struct_id': contract_30[0].struct_id.id,
    })
    
    # Crear línea de días trabajados (30 días)
    env['hr.payslip.worked_days'].create({
        'payslip_id': payslip_30.id,
        'code': 'WORK100',
        'name': 'Días trabajados',
        'number_of_days': 30.0,
        'number_of_hours': 240.0,  # 30 días * 8 horas
    })
    
    # Crear payslip para empleado 2 (24 días)
    payslip_24 = env['hr.payslip'].create({
        'name': 'DEMO-002',
        'employee_id': employee_24.id,
        'contract_id': contract_24[0].id,
        'payslip_run_id': payslip_run.id,
        'date_from': date_from,
        'date_to': date_to,
        'struct_id': contract_24[0].struct_id.id,
    })
    
    # Crear línea de días trabajados (24 días)
    env['hr.payslip.worked_days'].create({
        'payslip_id': payslip_24.id,
        'code': 'WORK100',
        'name': 'Días trabajados',
        'number_of_days': 24.0,
        'number_of_hours': 192.0,  # 24 días * 8 horas
    })
    
    # Calcular los payslips
    payslip_30.compute_sheet()
    payslip_24.compute_sheet()
    
    # Confirmar y procesar
    payslip_30.action_payslip_done()
    payslip_24.action_payslip_done()
    
    payslip_run.action_validate()
    
    return "Payslips demo creados exitosamente:\n- Empleado 1 (30 días): %s\n- Empleado 2 (24 días): %s\nLote: %s" % (
        payslip_30.name, payslip_24.name, payslip_run.name
    )


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    
    def create_demo_payslips(self):
        """Método para crear payslips demo desde la interfaz"""
        return create_demo_payslips(self.env)

