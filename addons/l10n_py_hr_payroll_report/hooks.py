# -*- coding: utf-8 -*-

def assign_accounts_paraguay(env):
    """
    Hook post-instalación: asignar cuentas contables paraguayas a reglas salariales
    
    Este hook se ejecuta después de instalar/actualizar el módulo y asigna
    las cuentas contables del plan paraguayo a las reglas salariales correspondientes.
    """
    # Desactivar reglas base de hr_payroll para evitar estructuras por defecto
    base_codes = [
        'BASIC',
        'GROSS',
        'ATTACH_SALARY',
        'ASSIG_SALARY',
        'CHILD_SUPPORT',
        'DEDUCTION',
        'REIMBURSEMENT',
        'NET',
    ]
    base_rules = env['hr.salary.rule'].with_context(active_test=False).search([
        ('code', 'in', base_codes)
    ])
    if base_rules:
        base_rules.write({'active': False})

    # Configurar estructura tipo Empleado Mensual - Paraguay
    structure_type = env.ref(
        'l10n_py_hr_payroll_report.structure_type_paraguay_monthly',
        raise_if_not_found=False,
    )
    if structure_type:
        values = {}

        if 'wage_type' in structure_type._fields:
            wage_selection = dict(structure_type._fields['wage_type'].selection or [])
            if 'monthly' in wage_selection:
                values['wage_type'] = 'monthly'

        if 'default_schedule_pay' in structure_type._fields:
            schedule_selection = dict(structure_type._fields['default_schedule_pay'].selection or [])
            if 'monthly' in schedule_selection:
                values['default_schedule_pay'] = 'monthly'

        struct = env.ref(
            'l10n_py_hr_payroll_report.hr_payroll_structure_es_produccion',
            raise_if_not_found=False,
        )
        if struct and 'default_struct_id' in structure_type._fields:
            values['default_struct_id'] = struct.id

        calendar = env.ref(
            'l10n_py_hr_payroll_report.resource_calendar_gt_sa',
            raise_if_not_found=False,
        )
        if calendar and 'default_resource_calendar_id' in structure_type._fields:
            values['default_resource_calendar_id'] = calendar.id

        if 'default_work_entry_type_id' in structure_type._fields:
            work_entry_type = env['hr.work.entry.type'].search([
                ('code', '=', 'WORK100')
            ], limit=1)
            if not work_entry_type:
                work_entry_type = env['hr.work.entry.type'].search([
                    ('name', 'ilike', 'asistencia')
                ], limit=1)
            if work_entry_type:
                values['default_work_entry_type_id'] = work_entry_type.id

        if values:
            structure_type.write(values)

    # Verificar si hr_payroll_account está instalado
    payroll_account_module = env['ir.module.module'].search([
        ('name', '=', 'hr_payroll_account'),
        ('state', '=', 'installed')
    ], limit=1)
    
    if not payroll_account_module:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("hr_payroll_account no está instalado. Las cuentas contables no se asignarán.")
        return
    
    # Ejecutar método para asignar cuentas
    try:
        result = env['hr.salary.rule'].with_context(active_test=False).assign_accounts_paraguay()
        if result and result.get('not_found'):
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning("Algunas cuentas no se encontraron: %s", result.get('not_found'))
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.error("Error al asignar cuentas contables: %s", str(e))
