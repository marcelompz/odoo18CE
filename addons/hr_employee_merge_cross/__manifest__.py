# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Merge (Crossnexion)',
    'version': '18.0.1.0.1',
    'category': 'Human Resources',
    'summary': 'Fusionar empleados duplicados redirigiendo todas las '
               'referencias (asistencias, nominas, contratos, etc.) al '
               'empleado maestro y archivando los duplicados.',
    'author': 'Crossnexion',
    'website': 'https://www.crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/hr_employee_merge_wizard_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True, 'application': False, 'auto_install': False,
}
