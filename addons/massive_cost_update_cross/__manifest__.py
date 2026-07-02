# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Actualización masiva de costos',
    'summary': 'Actualización masiva de los costos de las variantes de producto a partir de la lista de variantes.',
    'description': '''
        - Permite a los usuarios seleccionar varias variantes de producto y actualizar su precio (standard_price) simultáneamente.
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Inventory',
    'version': '26.3.13',
    'depends': [
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/massive_cost_update_wizard_view.xml',
    ],
}
