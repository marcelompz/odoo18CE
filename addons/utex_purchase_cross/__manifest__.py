# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Compras',
    'summary': 'Modulo que hereda del principal y agrega mejoras.',
    'description': '''
        - Modulo que hereda del principal y agrega mejoras al modulo de compras.
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.3.6',
    'depends': [
        'base',
        'purchase',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/purchase_order.xml',
    ],
}
