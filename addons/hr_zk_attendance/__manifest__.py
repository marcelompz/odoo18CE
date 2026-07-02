# -*- coding: utf-8 -*-
{
    'name': 'Biometric Device Integration',
    'version': '18.0.1.4.0',
    'category': 'Human Resources',
    'summary': "Integrating Biometric Device (Model: ZKteco uFace 202) With HR Attendance (Face + Thumb)",
    'description': "This module integrates Odoo with the biometric device (Model: ZKteco uFace 202), odoo18, odoo, hr, attendance. Crossnexion: Clear Data y Restart restringidos a admins, advertencias agregadas, accion segura para limpiar solo BD.",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base_setup', 'hr_attendance'],
    'external_dependencies': {
        'python': ['pyzk'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/biometric_download_wizard_views.xml',
        'views/biometric_device_details_views.xml',
        'views/hr_employee_views.xml',
        'views/daily_attendance_views.xml',
        'views/biometric_device_attendance_menus.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
