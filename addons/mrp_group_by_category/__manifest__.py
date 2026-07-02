{
    'name': 'MRP Group by Category',
    'version': '25.11.15',
    'category': 'Manufacturing',
    'summary': 'Agrupa las órdenes de producción por categoría de producto',
    'description': """
        Este módulo permite agrupar órdenes de producción por categoría de producto.
        Características:
        - Agrupa órdenes de producción por categoría
        - Crea una orden de producción agrupada
        - Agrupa componentes y tareas
        - Vista kanban para seguimiento de tareas
        - Botón inteligente en ventas para ver órdenes de producción
        - Wizard para configuración de fabricación
    """,
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': [
        'base',
        'mrp',
        'sale_management',
        'stock',
        'sale_detalles',
    ],
    'data': [
        # Seguridad
        'security/ir.model.access.xml',
        
        # Vistas
        'views/product_category_view.xml',
        'views/mrp_production_wizard_views.xml',
        'views/mrp_production_inherit_sale_lines.xml',
        'views/mrp_production_kanban_workorders.xml',
        'views/sale_order_views.xml',
        'views/mrp_workorder_inherit_sale_lines.xml',
        'views/sale_order_line_pivot.xml',
        'views/res_config_settings_views.xml',
        'views/rollo_impresion_views.xml',
        'data/rollo_impresion_sequence.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 
