# -*- coding: utf-8 -*-
{
    'name': 'Excel Recipe Import',
    'version': '18.0.2.0.0',
    'summary': 'Import Products, MRP BoMs and POS BoMs from Excel Template with Validation',
    'author': 'Crossnexion',
    'category': 'Manufacturing',
    'external_dependencies': {
        'python': ['pandas', 'openpyxl', 'packaging'],
    },
    'depends': ['base', 'product', 'mrp', 'pos_product_bom'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_recipe_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
