# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - CRM Questions CheckList',
    'summary': 'Modulo de customización del CRM',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'category': 'Uncategorized',
    'license': 'OPL-1',
    'version': '25.5.19',
    'depends': [
        'base',
        'crm',
        'mail',
        'sale_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'data/questions_security.xml',
        'data/sequence.xml',
        'views/crm_lead.xml',
        'views/res_questions.xml',
        'views/res_key_questions.xml',
    ],
}
