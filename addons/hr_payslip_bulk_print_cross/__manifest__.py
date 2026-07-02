# -*- coding: utf-8 -*-
{
    'name': 'Impresion Masiva de Recibos de Nomina (Crossnexion)',
    'version': '18.0.1.2.23',
    'category': 'Human Resources/Payroll',
    'summary': 'Multiples tipos de recibos PY: IPS, Interno, Bonificacion, '
               'Vacaciones (formato compacto 2 copias por hoja A4) + '
               'impresion masiva configurable.',
    'description': """
Impresion Masiva + Recibos Compactos PY - Crossnexion
======================================================

Cinco tipos de recibos preconfigurados:

* RECIBO IPS              - Salario Bruto, IPS, Faltas, Embargo
* RECIBO INTERNO          - Salario Bruto, IPS, Anticipos, Prestamo
* RECIBO BONIFICACION     - BNR, BNEX, CP, HE Diurnas/Nocturnas, Feriados
* RECIBO VACACIONES       - CN_VACACIONES (visible solo si hay valor)
* RECIBO AGUINALDO        - via modulo hr_payroll_holiday_pay_py_cross

Caracteristicas
---------------
* Formato A4 vertical compacto con 2 copias por hoja croquelada
  (COPIA EMPRESA / COPIA EMPLEADO) para los recibos IPS, Interno y
  Vacaciones.
* Logo + datos res.company en cada copia.
* Identificador prominente del tipo de recibo.
* Botones individuales en hr.payslip que se ocultan automaticamente
  si no aplican (bonificacion / vacaciones).
* Wizard de impresion masiva configurable que permite elegir cualquier
  reporte instalado, generar PDFs separados (ZIP) o consolidado.
* Flags por regla salarial (appears_on_*_receipt) para configurar
  manualmente que reglas aparecen en cada tipo de recibo.

Autor: Crossnexion / Orlando Lauseker
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_payroll',
        'l10n_py_hr_payroll_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_actions_server.xml',
        'data/hr_salary_rule_receipt_data.xml',
        'report/report_payslip_recibos_compactos.xml',
        'report/report_payslip_recibos_compactos_templates.xml',
        'wizard/hr_payslip_bulk_print_wizard_views.xml',
        'wizard/hr_payslip_batch_review_wizard_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hide_l10n_py_buttons.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
