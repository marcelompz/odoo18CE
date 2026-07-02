# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Factura Proveedor',
    'summary': 'Modulo que agrega un icono de acceso directo a factura proveedores',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.3.6',
    'depends': [
        'base',
        'account',
        'electronic_invoice_cross',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/account_supplier_stamping.xml',
        'views/res_partner.xml',
    ],
}
