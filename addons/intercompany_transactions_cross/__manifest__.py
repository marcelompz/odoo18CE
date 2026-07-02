# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Transacciones entre empresas',
    'summary': 'Automatice la creación de órdenes de venta a partir de órdenes de compra con margen personalizado.',
    'description': '''
        - Automatice la creación de órdenes de venta a partir de órdenes de compra con margen personalizado.
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.3.13',
    'depends': [
        'purchase',
        'sale'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/create_sale_order_wizard_views.xml',
        'data/ir_actions_server.xml',
    ],
}
