{
    'name': 'Sale Order Pivot Category',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Extiende la vista pivot de líneas de venta con categoría de producto',
    'description': """
        Este módulo extiende la vista pivot de las líneas de venta (sale.order.line)
        para incluir la categoría del producto como campo agrupable.
    """,
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': ['sale', 'product'],
    'data': [
        'views/sale_order_views.xml',
        'views/sale_order_pivot.xml',
        'views/cronograma_produccion.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 