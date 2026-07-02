# -*- coding: utf-8 -*-
{
    'name': 'Portal Detalles',
    'version': '25.10.06',
    'category': 'Sales/Portal',
    'summary': 'Sistema de carga de listas de productos desde el portal web',
    'description': """
Portal Detalles
===============

Este módulo permite a los comerciales generar enlaces para que los clientes 
carguen listas de productos desde el portal web de Odoo.

Funcionalidades:
* Configuración de listas portal por pedido y cliente
* Generación de enlaces únicos con tokens de acceso
* Formulario web tipo tabla para carga masiva de productos
* Sistema de notificaciones automáticas
* Seguimiento del estado de las listas
* Integración completa con el portal de Odoo

    """,
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': [
        'base',
        'sale',
        'portal',
        'website',
        'mail',
        'product',
    ],
    'data': [
        # Seguridad
        'security/portal_detail_security.xml',
        'security/ir.model.access.csv',
        
        # Datos
        'data/email_templates.xml',
        'data/portal_test_data.xml',
        
        # Vistas
        'views/portal_detail_config_views.xml',
        'views/portal_detail_list_views.xml',
        'views/portal_detail_menu.xml',
        
        # Templates del portal
        'views/portal_detail_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_frontend': [
            'portal_detalles/static/src/js/portal_detail.js',
            'portal_detalles/static/src/css/portal_detail.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
}
