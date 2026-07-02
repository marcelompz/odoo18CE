# -*- coding: utf-8 -*-
{
    'name': 'Tiempo Personal Remunerado / No Remunerado (Crossnexion)',
    'version': '18.0.1.2.3',
    'category': 'Human Resources/Time Off',
    'summary': 'Doble aprobacion (gerente + RRHH) y descuento automatico '
               'por tiempo personal no remunerado en nomina y asistencia.',
    'description': 'Ver GUIA_DE_USO.md',
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': [
        'base', 'hr', 'hr_attendance', 'hr_holidays', 'hr_payroll',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_salary_rule_data.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_approval_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
