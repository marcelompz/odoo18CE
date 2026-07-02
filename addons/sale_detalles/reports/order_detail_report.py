from odoo import api, models

class OrderDetailReport(models.AbstractModel):
    _name = 'report.sale_detalles.order_detail_report_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
            'data': data,
        } 