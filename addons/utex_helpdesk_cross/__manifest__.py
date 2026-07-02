# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Soporte al cliente',
    'summary': 'Modulo que hereda del principal y agrega mejoras',
    'description': '''
        - Menú root de acceso directo a nuevo ticket
        - Cambio de widget del campo prioridad
        - Boton `Convertir a oportunidad` aparece desde las siguientes etapas en el ticket
        - Concatenación de campos para el display_name Maquinas y herramientas
        - Devolución a la vista de lista al crear un ticket
        - Menu root a `Mis tickets`
        - Campo Nro etiqueta en Maquinas y herramientas
        - Campo Tipo de problema en ticket
        - Cambio de seleccion de campos de equipo de soporte y tipo de problema
        - Muestra los clientes dependiendo del usuario logueado
        - Muestra los equipos afectados dependiendo del equipo de soporte al cliente
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '25.12.14',
    'depends': [
        'base',
        'helpdesk',
        'maintenance',
        'crm_helpdesk',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_ticket.xml',
        'views/helpdesk_team.xml',
        'views/maintenance_equipment.xml',
        'views/maintenance_type_problem.xml',
        'views/res_users.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'utex_helpdesk_cross/static/src/scss/priority_styles.scss',
        ],
    },
}
