# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Coste en Destino',
    'summary': 'El módulo acorta los pasos para generar un coste en destino.',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'category': 'Uncategorized',
    'version': '26.3.5',
    'depends': [
        'base',
        'purchase',
        'stock_landed_costs',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/purchase_order.xml',
        'views/product_template.xml',
        'views/stock_landed_cost.xml',
        'views/product_category.xml',
    ],
}
