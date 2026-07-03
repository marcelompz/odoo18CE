# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - POS Factura Electrónica',
    'summary': 'Modulo de facturación electrónica de localización paraguaya en el PdV',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Point of Sale',
    'version': '18.0.1.0.1',
    'depends': [
        'point_of_sale',
        'l10n_py',
        'electronic_invoice_cross',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            # 'pos_einvoice_cross/static/src/app/screens/partner_list/partner_editor/partner_editor.xml',
            'pos_einvoice_cross/static/src/overrides/models/pos_store.js',
            # 'pos_einvoice_cross/static/src/app/screens/partner_list/partner_editor/partner_editor.js',
            # 'pos_einvoice_cross/static/src/app/screens/partner_list/partner_editor/partner_search.js',
            'pos_einvoice_cross/static/src/app/screens/partner_list/partner_line.xml',
        ]
    },
}
