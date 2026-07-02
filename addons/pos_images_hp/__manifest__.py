# -*- coding: utf-8 -*-
{
    'name': 'POS Images HP',
    'version': '18.0.25.10.05',
    'summary': 'Usa imágenes de alta calidad (image_1920) en el Punto de Venta',
    'description': '''
        Este módulo reemplaza las imágenes estándar del POS por versiones de alta resolución (image_1920) 
        para mejorar la presentación visual de los productos.
        
        Características:
        - Utiliza image_1920 como imagen principal en el POS
        - Fallback a image_1024 si image_1920 no está disponible
        - Configuración habilitada/deshabilitada desde la configuración del POS
        - Compatible con modo offline del POS
        - Optimizado para rendimiento
    ''',
    'author': 'Ing. Daril Díaz',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'product'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_images_hp/static/src/js/pos_images_hp.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'auto_install': False,
}
