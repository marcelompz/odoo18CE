# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Recibo de Dinero',
    'summary': 'Módulo para generar recibo de dinero en Odoo',
    'description': """
        El módulo permite generar un recibo de dinero en Odoo, el cual puede ser impreso y enviado al cliente,
        con la opción de agregar los pagos realizados por el cliente, las retenciones y las notas de crédito.
    """,
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.3.3',
    'depends': [
        'base',
        'account',
        'web',
        'electronic_invoice_cross'
    ],
    'data': [
        'data/ir_sequence.xml',
        'data/report_paperformat.xml',
        'security/ir.model.access.csv',
        'reports/advanced_receipt_payments.xml',
        'views/account_move.xml',
        'views/advanced_receipt_payments.xml',
        'views/account_payment.xml',
        'views/res_config_settings.xml',
        'wizard/receipt_money_group_wizard.xml',
        'wizard/add_withholdings_receiptmoney_wizard.xml',
    ],
}
