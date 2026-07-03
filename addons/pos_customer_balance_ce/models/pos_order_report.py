from odoo import models

class ReportPosOrder(models.Model):
    _inherit = 'report.pos.order'

    def _from(self):
        res = super()._from()
        
        # We append a WHERE clause to exclude the Settle Due product from the POS sales reports.
        # This ensures that debt collections do not inflate the sales figures.
        res += """
            WHERE l.product_id NOT IN (
                SELECT res_id 
                FROM ir_model_data 
                WHERE module = 'pos_customer_balance_ce' 
                  AND name = 'product_product_settle_due'
            )
        """
        return res
