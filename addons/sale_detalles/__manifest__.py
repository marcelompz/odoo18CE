{
    'name': 'Información Técnica de Ventas',
    'version': '25.11.15',
    'category': 'Sales',
    'summary': 'Agrega información técnica a las órdenes de venta',
    'description': """
        Este módulo agrega una sección de información técnica a las órdenes de venta,
        permitiendo:
        * Gestión de preguntas y respuestas técnicas
        * Notas técnicas en formato HTML
        * Preguntas recurrentes predefinidas
        * Importación de detalles de venta
        * Vista de calendario por fecha de vencimiento
        * Reportes de calendario con cantidad de productos
    """,
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': ['sale', 'product', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_product.xml',
        'data/technical_questions_data.xml',
        'data/sale_stage_data.xml',
        'data/model_type_data.xml',
        'data/paperformat_order_detail.xml',
        'data/sale_detalles_config_data.xml',
        'reports/order_detail_report_template.xml',
        'reports/sale_order_calendar_report_template.xml',
        'reports/report.xml',
        'views/order_detail_model_lines_views.xml',
        'views/actions.xml',
        'views/import_wizard_views.xml',
        'views/technical_info_views.xml',
        'views/order_detail_actions.xml',
        'views/sale_order_views.xml',
        'views/sale_order_calendar_views.xml',
        'views/sale_order_kanban_views.xml',
        'views/sale_stage_views.xml',
        'views/model_type_views.xml',
        'views/sale_detalles_config_views.xml',
        'views/menu_views.xml',
        'views/model_design_history_views.xml',
        'views/sale_order_portal_views.xml',
        'views/date_management_wizard_views.xml',
        'views/show_models_wizard_views.xml',
        'views/show_description_wizard_views.xml',
        'views/product_product_inherit_show_in_import_reference.xml',
        'views/product_category_views.xml',
        'views/sale_order_template_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 
