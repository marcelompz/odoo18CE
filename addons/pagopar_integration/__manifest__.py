{
    'name': 'Pagopar Payment Integration',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Integración completa con Pagopar para procesar pagos en Paraguay',
    'description': """
    Pagopar Payment Integration for Odoo 18
    =====================================
    
    Este módulo proporciona una integración completa con la plataforma de pagos Pagopar,
    permitiendo procesar pagos de forma segura y eficiente en Paraguay.
    
    Características principales:
    * ✅ Procesamiento de pagos con Pagopar
    * ✅ Integración completa con sitio web y ecommerce
    * ✅ Portal del cliente con historial de pagos
    * ✅ Páginas de resultado personalizadas (éxito, pendiente, error, cancelado)
    * ✅ Formularios de pago responsive y modernos
    * ✅ Manejo de webhooks para notificaciones automáticas
    * ✅ Configuración segura de credenciales
    * ✅ Validación automática de transacciones
    * ✅ Soporte para múltiples métodos de pago (tarjetas, transferencias, efectivo)
    * ✅ Logging completo de transacciones
    * ✅ Interface responsive optimizada para móviles
    * ✅ Sistema de filtros y ordenamiento en portal
    * ✅ Verificación de estado de pagos en tiempo real
    * ✅ Menús independientes (sin dependencia de módulos contables)
    
    Funcionalidades Web:
    * Portal del cliente para ver historial de pagos
    * Páginas de checkout personalizadas para ecommerce
    * Widgets de selección de método de pago
    * Sistema de notificaciones y alertas
    * Diseño responsive y moderno
    * Integración con website_sale
    
    Autor: Valente Systems - Cristhel Valente
    """,
    'author': 'Valente Systems - Cristhel Valente',
    'website': 'https://valentesystems.com',
    'maintainers': ['cristhel_valente'],
    'license': 'LGPL-3',
    'depends': [
        'base',
        'payment',
        'portal',
        'website',
        'website_sale',
    ],
    'data': [
        'security/pagopar_security.xml',
        'security/ir.model.access.csv',
        'data/payment_provider_data.xml',
        'views/pagopar_config_views.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/payment_templates.xml',
    ],
    # 'demo': [
    #     'demo/pagopar_demo.xml',
    # ],
    'assets': {
        'web.assets_frontend': [
            'pagopar_integration/static/src/js/payment_form.js',
            'pagopar_integration/static/src/css/pagopar_payment.css',
        ],
        'web.assets_backend': [
            'pagopar_integration/static/src/js/backend_components.js',
        ],
    },
    'external_dependencies': {
        'python': ['requests', 'python-dateutil'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
