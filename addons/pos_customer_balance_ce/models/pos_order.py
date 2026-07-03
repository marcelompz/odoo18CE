from odoo import models, api, fields

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _process_order(self, order, existing_order):
        # Process the order normally first
        pos_order_id = super()._process_order(order, existing_order)
        
        pos_order = self.browse(pos_order_id)
        
        # Check if it's a settle due order
        settle_due_product = self.env.ref('pos_customer_balance_ce.product_product_settle_due', raise_if_not_found=False)
        if settle_due_product and pos_order.partner_id:
            for line in pos_order.lines:
                if line.product_id.id == settle_due_product.id and line.price_subtotal_incl > 0:
                    # It's a debt payment. 
                    # 1. The POS will naturally credit the Income Account of this product.
                    # 2. We need to create a compensating move to move this from Income to Accounts Receivable,
                    #    so it doesn't inflate Sales and actually pays the debt.
                    
                    amount = line.price_subtotal_incl
                    company = pos_order.company_id
                    partner = pos_order.partner_id
                    
                    # Find accounts
                    income_account = settle_due_product.property_account_income_id or settle_due_product.categ_id.property_account_income_categ_id
                    if not income_account:
                        income_account = company.account_default_pos_receivable_account_id # fallback
                        
                    receivable_account = partner.with_company(company).property_account_receivable_id
                    
                    if income_account and receivable_account:
                        # Create compensating move
                        move_vals = {
                            'journal_id': pos_order.session_id.config_id.journal_id.id,
                            'date': pos_order.date_order,
                            'ref': f"Compensación Abono TPV {pos_order.name}",
                            'line_ids': [
                                (0, 0, {
                                    'name': f"Reversión Venta TPV (Abono) {pos_order.name}",
                                    'account_id': income_account.id,
                                    'debit': amount,
                                    'credit': 0.0,
                                }),
                                (0, 0, {
                                    'name': f"Abono de Cuenta TPV {pos_order.name}",
                                    'account_id': receivable_account.id,
                                    'partner_id': partner.id,
                                    'debit': 0.0,
                                    'credit': amount,
                                })
                            ]
                        }
                        
                        move = self.env['account.move'].create(move_vals)
                        move.action_post()
                        
                        # Now automatically reconcile the credit line with open invoices
                        credit_line = move.line_ids.filtered(lambda l: l.account_id == receivable_account and l.credit > 0)
                        
                        if credit_line:
                            # Find open invoices (debit lines in receivable)
                            open_invoices = self.env['account.move.line'].search([
                                ('partner_id', '=', partner.id),
                                ('account_id', '=', receivable_account.id),
                                ('move_id.state', '=', 'posted'),
                                ('reconciled', '=', False),
                                ('debit', '>', 0)
                            ], order='date asc')
                            
                            if open_invoices:
                                (open_invoices + credit_line).reconcile()
                                
        return pos_order_id
