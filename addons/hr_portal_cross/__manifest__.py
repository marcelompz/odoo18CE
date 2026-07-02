# -*- coding: utf-8 -*-
{
    'name': 'Portal Talento Humano (Crossnexion)',
    'version': '18.0.1.6.3',
    'category': 'Human Resources',
    'summary': 'Portal unificado de RRHH con tiles configurables, '
               'categorias, KPIs, feriados con imagenes y mensajes, '
               'y alertas de cumpleanos.',
    'description': """
v18.0.1.6.0
============
* Tile "Reclutamiento" en la columna Busqueda y Seleccion
* Tile "Manual de Funciones" en la columna Busqueda y Seleccion
* Nuevo modelo talent.holiday: feriados con imagen y mensaje reflexivo
* Kanban visual de feriados, accion para enviar aviso a todos los empleados
* Preseed de feriados Paraguay 2026
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/talent_portal_tile_views.xml',
        'views/hr_employee_birthday_views.xml',
        'views/talent_holiday_views.xml',
        'data/talent_portal_tile_data.xml',
        'data/talent_holiday_data.xml',
        'data/birthday_cron_data.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_portal_cross/static/src/scss/portal.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
