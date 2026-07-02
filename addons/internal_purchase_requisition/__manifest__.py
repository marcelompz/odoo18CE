# -*- coding: utf-8 -*-
{
    'name': "Purchase Request",

    'summary': "Employee Purchase Requisition Module for streamlined purchase approvals.",
    'license': 'Other proprietary',
    'author': "Infintor Solutions",
    'website': "https://www.infintor.com",
    'category': 'Uncategorized',
    'version':'18.0.1.0',
    "price": 10,
    "currency": 'USD',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','product','purchase'],
    'images': ['static/description/banner.png'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/requisition_view.xml',
        'views/report_purchase_requisition.xml',
        'views/site_request_material.xml',
        'views/partner_form_inherit.xml',
        'views/views.xml',
        'data/ir_sequence_purchase_requestion.xml'
    ],
    'installable': True,
    'application': True,
}

