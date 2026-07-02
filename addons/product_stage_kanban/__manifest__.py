{
    'name': 'Etapas de Producto Kanban',
    'version': '25.09.22',
    'category': 'Inventory/Inventory',
    'summary': 'Añade una vista kanban para productos, agrupados por etapas personalizadas.',
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_stage_views.xml',
        'views/product_template_views.xml',
        'data/product_stage_data.xml',
        'views/product_description_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
