# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Envío de DE por correo',
    'summary': 'Módulo para enviar documentos electrónicos por correo',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'category': 'Uncategorized',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'electronic_invoice_cross',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/ir_mail_server.xml',
        'views/account_move.xml',
        'views/stock_picking.xml',
        'views/res_config_settings.xml',
    ],
    'external_dependencies': {
        'python': ['dnspython'],
    },
}
