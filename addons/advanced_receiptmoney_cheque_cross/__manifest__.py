# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Recibo de dinero con cheque',
    'summary': 'Este módulo agrega el recibo de dinero del pago con cheque.',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '25.9.2',
    'depends': [
        'base',
        'advanced_receiptmoney_cross',
        'cheque_management_cross',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/advanced_receipt_payments_cheques.xml',
        'views/account_cheque_payment.xml',
        'reports/advanced_receipt_payments.xml',
        'wizard/cheque_receipt_money_group_wizard.xml',
    ],
}
