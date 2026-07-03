from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Hook to ensure necessary accounting setup for the POS debt settlement feature upon module installation.
    """
    # 1. Asignar cuentas de ingresos/gastos al producto Abono de Cuenta
    product = env.ref('pos_customer_balance_ce.product_product_settle_due', raise_if_not_found=False)
    if product:
        income_account = env['account.account'].search([('account_type', '=', 'income')], limit=1)
        expense_account = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
        
        if income_account and not product.property_account_income_id:
            product.property_account_income_id = income_account
        if expense_account and not product.property_account_expense_id:
            product.property_account_expense_id = expense_account

    # 2. Asignar 'Default POS Receivable Account' a las compañías si les falta
    companies = env['res.company'].search([])
    for company in companies:
        if not company.account_default_pos_receivable_account_id:
            receivable_account = env['account.account'].search([
                ('account_type', '=', 'asset_receivable'),
                ('company_ids', 'in', company.id)
            ], limit=1)
            
            if not receivable_account:
                receivable_account = env['account.account'].search([
                    ('account_type', '=', 'asset_receivable'),
                    ('company_id', '=', company.id)
                ], limit=1)
                
            if receivable_account:
                company.account_default_pos_receivable_account_id = receivable_account
