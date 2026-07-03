{
    'name': 'Mass Product Import with Inventory',
    'version': '18.0.1.4.0',
    'category': 'Inventory/Products',
    'summary': 'Import products massively from Excel or manual entry with initial stock quantities',
    'description': """
        Mass Product Import with Inventory
        ==================================
        This module allows creating products massively with initial stock quantities through:

        * Excel file import (.xlsx format)
        * Manual batch entry directly in Odoo with validation

        Features:
        ---------
        - Download Excel template with predefined structure
        - Automatic category creation (Product & POS categories)
        - Initial stock quantity assignment via stock.quant
        - Product tracking configuration (None, Lot, Serial)
        - POS availability flag
        - Duplicate barcode validation (database + internal file)
        - Preview and validation before creation
        - OPTIMIZED: Batch processing for large imports (1000+ products)

        Column mapping (Excel):
        -----------------------
        1. Internal Reference (required)
        2. Product Name (required)
        3. POS Description
        4. Barcode
        5. Available in POS (TRUE/FALSE)
        6. Product Category
        7. POS Category
        8. Sales Price (optional, default 0)
        9. Cost Price (optional, default 0)
        10. Quantity on Hand (optional, default 0)
        11. Product Type (Goods/Service/Combo)
        12. Tracking (None/Lot/Serial)
        
        Performance notes:
        ------------------
        - Uses batch queries to avoid N+1 problem
        - Validates all barcodes in a single SQL query
        - Creates all products in one operation
        - Recommended for imports of 1000+ products
    """,
    'author': 'Crossnexion E.A.S.',
    'website': 'https://www.crossnexion.com',
    'license': 'OPL-1',
    'depends': ['product', 'stock', 'point_of_sale'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/product_mass_import_wizard_views.xml',
        'views/product_batch_import_views.xml',
        'views/menu_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
