{
    'name': 'Product Variant Image and Price Changer',
    'version': '18.0.1.0.0',
    'category': 'Website/E-commerce',
    'summary': 'Permite cambiar la imagen y el precio del producto al seleccionar variantes',
    'description': """
        Este módulo extiende la funcionalidad de Odoo para permitir a los usuarios
        cambiar la imagen principal y el precio de un producto en la página de la tienda
        al hacer clic en diferentes imágenes de variantes de producto.
        
        Características:
        - Gestión de imágenes por variante de producto
        - Cambio dinámico de imagen principal al hacer clic
        - Actualización automática del precio según la variante
        - Interfaz intuitiva en el frontend
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': ['website_sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_frontend_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'product_variant_image_changer/static/src/js/product_variant_changer.js',
            'product_variant_image_changer/static/src/css/product_variant_changer.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

