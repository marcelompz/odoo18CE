# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Gestión de cheques - Edición Enterprise',
    'summary': 'Administre cheques posfechados con funciones avanzadas como compatibilidad con múltiples divisas, prorrateo en pagos de facturas y más.',
    'description': """
        Este módulo proporciona una gestión integral de cheques posfechados en Odoo. Los cheques posfechados son cheques emitidos con fecha futura, que en algunos países pueden no cobrarse ni depositarse hasta esa fecha. Nuestro módulo cubre esta necesidad en Odoo al permitir el registro, seguimiento y gestión de estos cheques en diferentes estados.

        Características clave:
        - Compatibilidad total con múltiples divisas para cheques
        - Prorrateo de pagos entre varias facturas
        - Asignación automática de saldos de cheques restantes como crédito para clientes o proveedores
        - Informes detallados en PDF para seguimiento y auditoría
    """,
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Accounting',
    'version': '25.5.14',
    'depends': [
        'account_accountant',
        'cheque_management_cross',
    ],
    'data': [
        'views/account_cheque_payment.xml',
    ],
}
