# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Ventas',
    'summary': 'Modulo que agrega funcionalidades de ventas.',
    'description': """
        - Modulo que agrega funcionalidades de ventas.
    """,
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.3.6',
    'depends': [
        'base',
        'sale_management',
        'electronic_invoice_cross',
        'sale_detalles',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order.xml',
        'report/report_sale_bom_requirements.xml',
    ],
}
