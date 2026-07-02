{
    'name': 'Simplificador de Checkout Web para Odoo',
    'version': '1.0',
    'category': 'Sitio Web',
    'summary': 'Simplifica el proceso de compra en Odoo combinando los pasos de dirección y pago.',
    'description': """
        Este módulo simplifica el proceso de compra en el sitio web de Odoo.
        Combina los pasos de dirección y pago en una sola vista.
        Muestra mensajes condicionales para transferencias bancarias según el método de pago seleccionado mediante JavaScript.
        Además, permite a los usuarios subir un archivo durante la compra, que se guarda como comentario en la orden de venta.
    """,
    'author': 'Ing. Daril Diaz',
    'depends': ['website', 'website_sale', 'payment', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/checkout_layout.xml',
        'views/website_sale_templates.xml',
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Aquí puedes incluir solo los archivos JS/CSS que realmente necesitas
            # Por ejemplo, tu propio CSS o JS puro (si lo necesitas)
            # 'web_checkout_simplifier/static/src/css/checkout_simplifier.css',
            # 'web_checkout_simplifier/static/src/js/checkout_simplifier_puro.js',
        ],
        # Puedes crear un bundle exclusivo para tu checkout:
        'web_checkout_simplifier.assets_checkout': [
            # Solo los archivos necesarios para tu checkout
            # 'web_checkout_simplifier/static/src/css/checkout_simplifier.css',
            # 'web_checkout_simplifier/static/src/js/checkout_simplifier_puro.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

