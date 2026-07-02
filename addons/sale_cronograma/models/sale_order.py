from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mostrar_en_reportes = fields.Boolean(
        string='Mostrar en Cronograma',
        default=True,
        help='Si está activo, esta orden aparecerá en los reportes de cronograma'
    )

