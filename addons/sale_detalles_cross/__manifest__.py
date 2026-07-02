# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Sale Detalles',
    'summary': 'Modulo que hereda del principal y ajusta los requerimientos del cliente',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.4.6',
    'depends': [
        'base',
        'sale_detalles'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order.xml',
        'wizard/show_image_wizard.xml',
    ],
}
