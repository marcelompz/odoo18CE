{
    'name': 'Automated Validation of Product Delivery by Lot',
    'version': '18.0.1.0.1',
    'category': 'Inventory/Delivery',
    'summary': 'Automates validation and lot assignment for outgoing pickings with negative inventory management.',
    'description': """
        Features:
        - View of pending outgoing pickings assigned but not validated.
        - Automatic lot assignment (FIFO) for move lines.
        - Negative inventory handling with specific models and tracking.
        - Reports and logging for negative inventory cases.
    """,
    'author': 'Antigravity',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/stock_picking_views.xml',
        'views/lot_validation_log_views.xml',
        'views/stock_negative_record_views.xml',
        'report/stock_negative_record_report.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
