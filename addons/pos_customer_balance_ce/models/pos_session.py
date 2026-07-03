from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super().load_pos_data()
        
        # Inject the settle due product id
        settle_due_product = self.env.ref('pos_customer_balance_ce.product_product_settle_due', raise_if_not_found=False)
        if settle_due_product:
            loaded_data['pos_customer_balance_ce.product_id'] = settle_due_product.id
        else:
            loaded_data['pos_customer_balance_ce.product_id'] = False

        loaded_data['pos_customer_balance_ce.auto_invoice'] = self.config_id.auto_invoice_debt_payment
            
        return loaded_data


    def _get_sale_key(self, base_line):
        key = super()._get_sale_key(base_line)
        settle_due_product = self.env.ref('pos_customer_balance_ce.product_product_settle_due', raise_if_not_found=False)
        if settle_due_product and base_line['product_id'].id == settle_due_product.id:
            # Group by partner so the receivable account doesn't fail
            key['partner_id'] = base_line['record'].order_id.partner_id.id
            # Ensure it uses the company's default POS receivable account or partner's receivable account
            partner = base_line['record'].order_id.partner_id
            if partner:
                accounting_partner = self.env["res.partner"]._find_accounting_partner(partner)
                key['account_id'] = accounting_partner.property_account_receivable_id.id
        return key

    def _get_sale_vals(self, key, sale_vals):
        vals = super()._get_sale_vals(key, sale_vals)
        if 'partner_id' in key:
            vals['partner_id'] = key['partner_id']
        return vals
