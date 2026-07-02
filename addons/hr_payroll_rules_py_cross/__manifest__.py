# -*- coding: utf-8 -*-
{
    'name': 'Reglas Salariales Paraguay (Crossnexion)',
    'version': '18.0.2.10.4',
    'category': 'Human Resources/Payroll',
    'summary': 'Reglas salariales basicas y complementarias de Paraguay '
               '(Bruto, IPS, Bonificaciones, Vacaciones, Aguinaldo, '
               'Anticipos, Embargos, FALTAS, HE Diurno/Nocturno, '
               'pestana Tablero en recibo, jornalero/mensualizado por '
               'tipo de contrato, historial de pagos en empleado).',
    'description': """
Reglas Salariales Paraguay - Crossnexion
========================================
- 16+ reglas salariales paraguayas auto-aplicadas a estructuras
- Pestana "Marcaciones del periodo" en recibo
- Pestana "Detalle de marcaciones" en recibo
- Pestana "Historial de Pagos" en empleado
- Boton "Solicitar Aprobacion de FALTAS" via hr.leave
- Mensualizado vs Jornalero segun tipo de contrato
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_payroll', 'hr_holidays', 'hr_contract',
                'hr_attendance_shift_groups'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_salary_rule_data.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_payslip_attendance_views.xml',
        'views/hr_contract_type_views.xml',
        'views/hr_employee_history_views.xml',
        'views/hr_payslip_input_views.xml',
        'views/hr_account_mapping_views.xml',
        'views/hr_aguinaldo_views.xml',
        'views/hr_payslip_payment_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
}
