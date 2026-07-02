# -*- coding: utf-8 -*-
{
    'name': 'Pago Quincenal Automatizado (Crossnexion)',
    'version': '18.0.1.1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Anticipo quincenal automatico (50% bruto + ajustes IPS proporcional '
               'a dias, mas anticipos extraordinarios pendientes). Tipos de '
               'prestamo (prestamo/uniforme/beneficio). Antiguedad minima para '
               'prestamo. Regla salarial CN_ANTICIPO_QUINCENAL.',
    'description': """
Pago Quincenal Automatizado - Paraguay
=======================================

Funcionalidades
---------------
* Configuracion en el contrato: "Aplica pago de quincena" (cn_paga_quincena).
* Configuracion empresa: antiguedad minima (dias) para solicitar prestamo.
* Tipos de prestamo: prestamo / uniforme / beneficio / otros.
* Validacion de antiguedad al aprobar un prestamo (no aplica a uniforme/beneficio).
* Cuota del prestamo comienza el MES SIGUIENTE al desembolso (no el mismo mes).
* Wizard "Generar Quincenas" que para cada empleado con cn_paga_quincena=True:
    - Bruto quincena      = wage x 50% x (dias_disponibles / 15)
    - IPS quincena (-)    = wage x 9% x 50% x (dias_disponibles / 15)
    - Extraordinarios (+) = Sigma(prestamos/uniformes desembolsados pendientes)
    - Neto quincenal      = bruto - IPS + extraordinarios
* Crea un hr.advance tipo "quincena" por el neto calculado, lo desembolsa y
  vincula los prestamos extraordinarios incluidos para su trazabilidad.
* Regla salarial CN_ANTICIPO_QUINCENAL descuenta el anticipo del recibo mensual.
* Las FALTAS NO se descuentan en la quincena, solo en el recibo de fin de mes.

Dependencias
------------
* hr_loan_advance_py_cross (Crossnexion) - modulo base de prestamos y anticipos.
* hr_payroll_rules_py_cross (Crossnexion) - reglas salariales PY.
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': [
        'base', 'hr', 'hr_payroll', 'account', 'mail',
        'hr_loan_advance_py_cross',
        'hr_payroll_rules_py_cross',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_benefit_type_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_benefit_type_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_loan_views.xml',
        'views/hr_advance_views.xml',
        'wizards/hr_quincena_generator_views.xml',
        'views/menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
