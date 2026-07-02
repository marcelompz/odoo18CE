# -*- coding: utf-8 -*-
{
    'name': "Libros IVA Venta/Compra",

    'summary': """
        Libros IVA Venta/Compra""",

    'description': """
        Libros IVA Venta/Compra.

        Solo se cambian las posiciones de las columnas en el excel.
        Se modifica calculo del total para que tenga en cuenta solo montos de registros que fueron publicados

        Tarea N° 151.194 GC - se procede a verificar y modificar calculo de exenta segun indicacion de la tarea.
    """,

    'author': "Valente Systems EAS – Cristhel Valente",
    'email': "soporte@valentesystems.com",
    'website': "https://www.valentesystems.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '26.6.9',

    # any module necessary for this one to work correctly
    'depends': ['base', 'report_xlsx', 'electronic_invoice_cross'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
