# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Fusion Avanzada de Documentos de Compra',
    'summary': 'Permite la fusión de Órdenes de Compra, Facturas de Proveedor y Recepciones.',
    'description': '''
        Modulo para unificar documentos de compras (PO, Facturas, Recepciones) manteniendo consistencia.
        - Fusión de Purchase Orders
        - Fusión de Vendor Bills
        - Fusión de Stock Pickings
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Purchase',
    'version': '26.3.24',
    'depends': [
        'purchase',
        'account',
        'stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_merge_wizard_views.xml',
    ],
}
