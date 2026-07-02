{
    "name": "All In One Stock Reports",
    "summary": """
        Export stock reports in multiple formats
    """,
    "description": """
    """,
    "author": "Miftahussalam",
    "website": "https://blog.miftahussalam.com/",
    "category": "Inventory/Inventory",
    "version": "26.2.23",
    "depends": [
        "base",
        "stock",
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/report_paperformat.xml",
        "views/current_stock_templates.xml",
        "views/stock_card_detail_templates.xml",
        "views/stock_card_summary_templates.xml",
        "views/stock_movement_templates.xml",
        "wizard/ms_stock_report_wizard_views.xml",
    ],
    "demo": [

    ],
    "images": [
        "static/description/images/main_screenshot.png",
    ],
    "license": "OPL-1",
    "price": 30,
    "currency": "USD",
    "live_test_url": "https://odoo18.miftahussalam.com/",
}
