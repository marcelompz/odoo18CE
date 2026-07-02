# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Contabilidad',
    'summary': 'Modulo que hereda del principal y agrega mejoras',
    'description': """
        - Modulo que hereda del principal y agrega mejoras en la contabilidad solicitadas por el cliente.
    """,
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.6.10',
    'depends': [
        'base',
        'account',
        'electronic_invoice_cross',
        'l10n_latam_invoice_document',
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/account_payment.xml',
        'views/account_move.xml',
        'views/l10n_latam_document_type.xml',
        'views/res_config_settings_views.xml',
        'reports/delinquent_customer_report_cross.xml',
        'wizard/account_payment_register.xml',
        'wizard/delinquent_customer_report_cross.xml',
    ],
}
