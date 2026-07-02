# -*- coding: utf-8 -*-
{
    'name': "Resolución 77 - Depreciación Activo Fijo",

    'summary': """
        Cuadro de Depreciación de Bienes del Activo Fijo - Resolución General N° 77/2020 SET
        """,

    'description': """
        Módulo para gestionar el Cuadro de Depreciación de los Bienes del Activo Fijo 
        según el formato exigido por la SET (Resolución General N° 77/2020).
        
        Funcionalidades principales:
        - Registro y visualización del cuadro de depreciación
        - Cálculo automático de depreciación fiscal 
        - Validación del Valor Fiscal Residual
        - Exportación a Excel en formato oficial
        - Gestión de porcentajes y vida útil
        - Soporte para diferentes fechas de cierre fiscal
        - Integración completa con módulo contable
        - Generación automática de activos fijos
        - Creación de asientos contables de depreciación
    """,

    'author': "Valente Systems EAS – Cristhel Valente",
    'email': "soporte@valentesystems.com",
    'website': "https://www.valentesystems.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_asset'],

    # External dependencies
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/menus.xml',  # Cargar menús primero
        'views/resolucion_77_line.xml',
        'views/views.xml',
        'views/templates.xml',
        'wizard/export_wizard.xml',
        'wizard/accounting_config_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
} 
