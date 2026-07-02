{
    'name': 'Generador de Tareas desde Órdenes de Venta',
    'version': '1.0',
    'category': 'Sales/Project',
    'summary': 'Genera tareas y subtareas en proyectos desde órdenes de venta',
    'description': """
        Este módulo permite generar automáticamente tareas y subtareas en proyectos
        basadas en órdenes de venta. Permite configurar tareas simples y complejas
        que se generarán según la configuración del usuario.
    """,
    'author': 'Ing. Daril Diaz',
    'website': '',
    'depends': ['sale', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
        'views/task_template_views.xml',
        'wizard/task_generator_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 