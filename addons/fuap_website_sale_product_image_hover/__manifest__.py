# -*- coding: utf-8 -*-
{
    'name': "Website product image hover",

    'summary': "Allows you to define the image that is displayed when hovering the mouse over the product",

    'author': "Alejandro Molina",    
    'category': 'Website/Website',
    'version': '18.0.1.0',
    'license': 'OPL-1',
    'price': 15,
    'currency': 'EUR',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    'data': [
        'views/product_views.xml',
        'views/website_sale.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'fuap_website_sale_product_image_hover/static/src/scss/website_sale_backend.scss',
        ],
        'web.assets_frontend': [
            'fuap_website_sale_product_image_hover/static/src/scss/website_sale.scss',
            'fuap_website_sale_product_image_hover/static/src/js/website_sale.js',
        ],
    },

    'images': ['static/description/img/usage_image_hover.gif'],
}