# -*- coding: utf-8 -*-
{
    'name': 'Anticipos y Prestamos a Empleados (Crossnexion)',
    'version': '18.0.1.0.3',
    'category': 'Human Resources/Payroll',
    'summary': 'Anticipos de sueldo y prestamos a funcionarios con doble '
               'aprobacion (RRHH + Finanzas), asiento contable y descuento '
               'automatico en nomina.',
    'description': """
Anticipos y Prestamos a Empleados - Paraguay
=============================================

Modelos:
  * hr.advance  - Anticipo de sueldo (pago unico, descuento en 1 cuota)
  * hr.loan     - Prestamo a funcionario (pago unico, descuento en N cuotas)

Flujo de doble aprobacion:
  Borrador -> Aprobado RRHH -> Desembolsado Finanzas -> En curso -> Cerrado

Al desembolsar:
  - Se genera un account.payment (asiento: Debe Anticipo / Haber Caja-Banco)
  - Se crea un hr.salary.attachment con la cuota mensual
  - El recibo de nomina lo descuenta automaticamente via reglas
    CN_ANTICIPO y CN_PRESTAMO del modulo hr_payroll_rules_py_cross
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_payroll', 'account', 'mail'],
    'data': [
        'security/hr_loan_advance_security.xml',
        'security/ir.model.access.csv',
        'data/hr_loan_advance_sequence.xml',
        'data/hr_payslip_input_type_data.xml',
        'views/hr_advance_views.xml',
        'views/hr_loan_views.xml',
        'views/menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
