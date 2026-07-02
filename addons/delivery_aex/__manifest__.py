# -*- coding: utf-8 -*-
{
    'name': "AEX Delivery Integration",
    'summary': """
        Integrate Odoo with AEX for national shipping services in Paraguay.
    """,
    'description': """
        This module allows you to calculate shipping rates, generate shipments,
        print labels, and track packages with AEX directly from Odoo.
        - Rate calculation in eCommerce checkout.
        - Shipment confirmation and label generation from stock pickings.
        - Package tracking.
    """,
    'author': "Crossnexion EAS",
    'website': "www.crossnexion.com",
    'category': 'Inventory/Delivery',
    'version': '25.7.18',
    'depends': [
        'delivery',
        'product',
        'stock',
        'stock_delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_carrier_data.xml',
        'views/delivery_carrier.xml',
        'views/res_partner.xml',
        'wizard/aex_city_wizard.xml',
        'views/aex_city.xml',
        'views/menu.xml',
        'views/product_template.xml',
        'views/stock_picking.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
