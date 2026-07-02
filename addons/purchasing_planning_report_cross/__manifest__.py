{
    'name': 'Planificación de Compras',
    'version': '18.0.1.1.0',
    'category': 'Purchase',
    'summary': 'Reporte consolidado definitivo',
    'author': 'Crossnexion',
    'depends': ['purchase', 'stock', 'sale', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_report_wizard_views.xml',
        'views/purchase_report_views.xml',
    ],
    'installable': True,
    'license': 'OPL-1',
    'post_init_hook': 'post_init_hook',
}
