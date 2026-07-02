# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Anticipos en Órdenes de Venta',
    'summary': 'Permite registrar pagos de anticipo directamente desde una orden de venta confirmada.',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Sales/Sales',
    'version': '26.4.23',
    'depends': [
        'sale_management',
        'account',
        'sale_detalles',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order.xml',
        'views/res_config_settings.xml',
        'wizard/sale_advance_payment_wizard.xml',
    ],
}
