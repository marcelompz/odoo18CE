{
    'name': 'Reporte de Venta UX 335',
    'version': '18.0.1.0.1',
    'summary': 'Reporte personalizado de pedido de venta, producto comercial y presupuesto rápido (UX 335)',
    'description': """
        Reporte personalizado para pedidos de venta (UX - PRESUPUESTO 335).
        Producto comercial: lista de productos con precio para presupuestos rápidos.
        Presupuesto rápido: sección en el pedido de venta que no impacta inventario;
        el total se carga en una línea con el producto "Presupuesto".
    """,
    'author': 'Ing. Daril Diaz',
    'category': 'Ventas',
    'depends': ['sale', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/presupuesto_config_views.xml',
        'views/producto_comercial_views.xml',
        'views/sale_order_views.xml',
        'views/sale_menu_views.xml',
        'views/report_external_layout.xml',
        'reports/report_action.xml',
        'reports/report_template.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'changelog': {
        '18.0.1.0.1': {
            'changes': [
                '[#9509] Permitir crear productos comerciales directamente desde la pestaña "Presupuesto rápido" en línea de venta',
            ]
        }
    }
}
