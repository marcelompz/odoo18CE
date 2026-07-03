{
    'name': "Crossnexion - POS Customer Balance CE",
    'summary': """
        Adds customer outstanding balance column to POS client list screen in Odoo 18 Community Edition.
    """,
    'description': """
        This module extends the Point of Sale client list screen to display the outstanding debt
        of each customer. This version includes real-time calculation of pending POS orders.
    """,
    'author': 'Crossnexion E.A.S.',
    'website': 'https://www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Point of Sale',
    'version': '18.0.2.3.6',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/pos_payment_method_views.xml',
        'data/product_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_balance_ce/static/src/components/client_list_screen/client_list_screen.js',
            'pos_customer_balance_ce/static/src/components/client_list_screen/client_list_screen.xml',
            'pos_customer_balance_ce/static/src/components/client_list_screen/client_list_screen.scss',
            'pos_customer_balance_ce/static/src/overrides/models/pos_store.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
