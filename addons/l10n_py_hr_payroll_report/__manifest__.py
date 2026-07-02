# -*- coding: utf-8 -*-
{
    'name': 'Paraguay - Payroll Reports',
    'version': '26.01.05',
    'category': 'Human Resources/Payroll',
    'countries': ['py'],
    'summary': 'Reportes de nómina para Paraguay - Recibo de pago de sueldo según Ley 213/93',
    'description': """
        Módulo para generar recibos de pago de sueldo de funcionarios
        en formato paraguayo según legislación laboral.
        
        Características:
        - Generación de PDF con formato oficial
        - Incluye información del empleado y empresa
        - Desglose de haberes y descuentos
        - Cumple con normativa laboral paraguaya
        1
    """,
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': [
        'hr_payroll',
        'hr',
        'hr_contract',
        'hr_holidays',
        'hr_payroll_holidays',
        'hr_attendance',
        'base',
    ],
    'external_dependencies': {'python': ['xlsxwriter', 'num2words']},
    'data': [
        'security/ir.model.access.csv',
        # Reportes primero (necesarios para las estructuras salariales)
        'report/report_payslip_funcionario.xml',
        'report/report_payslip_funcionario_templates.xml',
        'report/report_payslip_ips.xml',
        'report/report_payslip_ips_templates.xml',
        'report/report_contract_py.xml',
        'report/report_contract_py_templates.xml',
        # Datos de nómina (referencian los reportes)
        'data/hr_payroll_py_data.xml',
        'data/hr_payroll_structure_import.xml',
        'data/hr_payroll_structure_fix.xml',
        'data/hr_holidays_data.xml',
        'data/hr_bonification_data.xml',
        'data/hr_minimum_wage_data.xml',
        'data/hr_resource_calendar_data.xml',
        'data/hr_payroll_summary_concept_data.xml',
        'data/hr_payroll_mtess_concept_data.xml',
        # Plantillas de contrato (después de los modelos y vistas)
       # 'data/hr_contract_templates.xml',
        # Vistas
        'views/rrhh_paraguay_menu.xml',
        'views/hr_employee_dependent_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_dependents_views.xml',
        'views/hr_contract_template_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_bonification_category_views.xml',
        'views/hr_bonification_views.xml',
        'views/hr_minimum_wage_views.xml',
        'views/hr_payroll_bank_export_views.xml',
        'views/hr_payroll_ips_export_views.xml',
        'views/create_demo_wizard_views.xml',
        'wizard/hr_payroll_report_wizard_views.xml',
        'views/hr_payslip_views.xml',
        'views/payslip_menu.xml',
        'views/hr_salary_attachment_views.xml',
        'views/hr_payroll_summary_concept_views.xml',
        'views/hr_payroll_mtess_concept_views.xml',
        'views/res_company_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': ['hr_payroll'],
    'license': 'LGPL-3',
    'post_init_hook': 'assign_accounts_paraguay',
}
