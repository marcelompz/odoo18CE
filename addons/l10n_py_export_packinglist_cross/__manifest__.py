# -*- coding: utf-8 -*-
{
    'name': 'Paraguay - Packing List de Exportacion',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Generacion de Packing List de Exportacion desde Nota de Remision (Paraguay)',
    'description': """
Packing List de Exportacion para Paraguay
==========================================
Modulo personalizado que permite generar un Packing List de exportacion
directamente desde una Nota de Remision (stock.picking).
""",
    'author': 'Crossnexion',
    'website': 'https://www.crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['stock', 'sale_stock', 'account', 'uom', 'utex_stock_cross'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizard/stock_packing_list_wizard_views.xml',
        'views/stock_packing_list_views.xml',
        'views/stock_picking_views.xml',
        'views/product_template_views.xml',
        'views/product_packaging_views.xml',
        'views/menu_views.xml',
        'report/report_packinglist.xml',
        'report/report_packinglist_document.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
