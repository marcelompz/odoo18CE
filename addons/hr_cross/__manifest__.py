# -*- coding: utf-8 -*-
{
    'name': 'RRHH Cross (Suite)',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Modulo paraguas: instala toda la suite de RRHH en orden.',
    'description': """
RRHH Cross - Suite
==================
Modulo paraguas. Instalar este modulo instala automaticamente, en el orden
correcto (via dependencias), todos los modulos custom de RRHH:

- hr_attendance_shift_groups   (turnos, tablero, correccion de marcaciones)
- hr_zk_attendance             (reloj biometrico ZKTeco)
- hr_employee_merge_cross
- hr_holidays_remunerated_cross
- hr_job_description_cross
- hr_loan_advance_py_cross
- hr_payroll_holiday_pay_py_cross
- hr_payroll_rules_py_cross
- hr_payslip_bulk_print_cross
- hr_portal_cross
- hr_quincena_cross
- l10n_py_hr_payroll_report

Librerias Python requeridas: pyzk, xlsxwriter, num2words.
""",
    'author': 'Crossnexion',
    'website': 'https://www.crossnexion.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_attendance_shift_groups',
        'hr_employee_merge_cross',
        'hr_holidays_remunerated_cross',
        'hr_job_description_cross',
        'hr_loan_advance_py_cross',
        'hr_payroll_holiday_pay_py_cross',
        'hr_payroll_rules_py_cross',
        'hr_payslip_bulk_print_cross',
        'hr_portal_cross',
        'hr_quincena_cross',
        'hr_zk_attendance',
        'l10n_py_hr_payroll_report',
    ],
    'external_dependencies': {'python': ['pyzk', 'xlsxwriter', 'num2words']},
    'data': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
