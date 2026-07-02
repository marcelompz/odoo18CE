# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Recibo de dinero con firma del empleado',
    'summary': 'Este módulo agrega la firma del empleado al recibo de dinero.',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '25.7.31',
    'depends': [
        'base',
        'hr',
        'advanced_receiptmoney_cross',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'views/advanced_receipt_payments.xml',
        'reports/advanced_receipt_payments.xml',
    ],
}
