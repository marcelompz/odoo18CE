from odoo import models, fields
from datetime import date, timedelta


class ReportPurchaseWizard(models.TransientModel):
    _name = 'report.purchase.wizard'
    _description = 'Filtro de Fechas - Reporte de Compras'

    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: date.today() - timedelta(days=90)
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=lambda self: date.today()
    )

    def action_generate_report(self):
        """Refresh the consolidated report with the chosen date range."""
        self.env['report.purchase.data.consolidated'].action_refresh_report(
            date_from=self.date_from,
            date_to=self.date_to
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Compras Consolidado',
            'res_model': 'report.purchase.data.consolidated',
            'view_mode': 'list,form',
            'target': 'main',
        }
