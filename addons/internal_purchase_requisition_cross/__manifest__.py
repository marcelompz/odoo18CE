# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Requisiciones de compra',
    'summary': 'Modulo que hereda del principal y agrega mejoras',
    'description': '''
        - Mejoras detallados en la documentacion interna.
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '26.4.20',
    'depends': [
        'internal_purchase_requisition',
        'hr',
        'product',
        'purchase',
        'utex_stock_cross',
        'utex_helpdesk_cross',
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/report_paperformat.xml',
        'views/purchase_requisition.xml',
        'views/hr_department.xml',
        'views/product_supplierinfo.xml',
        'views/product_template.xml',
        'views/purchase_order.xml',
        'views/stock_picking.xml',
        'views/product_packaging.xml',
        'views/product_product.xml',
        'report/purchase_requisition.xml',
        'report/purchase_report.xml',
        'wizard/mp_purchase_requisition_wizard.xml',
        'wizard/purchase_requisition_cancel_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'internal_purchase_requisition_cross/static/src/custom_styles.scss',
        ],
    },
}
