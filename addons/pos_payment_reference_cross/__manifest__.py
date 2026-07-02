# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Referencia de pago en el PdV',
    'summary': 'Agrega un campo de referecia de pago en el PdV',
    'description': '''
        - El módulo agrega un campo para carga de referencia del pago en el PdV
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Point of Sale',
    'version': '26.3.10',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_payment_method.xml',
        'views/pos_payment.xml',
        'views/pos_order.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_reference_cross/static/src/js/payment_model.js',
            'pos_payment_reference_cross/static/src/js/payment_screen.js',
            'pos_payment_reference_cross/static/src/xml/payment_screen.xml',
        ],
    },
    'installable': True,
}
