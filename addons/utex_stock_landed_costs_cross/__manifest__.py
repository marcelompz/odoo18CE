# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Coste en destino avanzado',
    'summary': 'Modulo que hereda de principal para añadir requerimientos del cliente',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'category': 'Uncategorized',
    'version': '25.4.23',
    'depends': [
        'base',
        'stock_landed_costs_cross',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template.xml',
        'wizard/stock_landed_costs_wizard.xml',
    ],
}
