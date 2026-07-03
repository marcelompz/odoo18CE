from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    auto_invoice_debt_payment = fields.Boolean(
        string='Facturar Abonos de Cuenta',
        default=False,
        help='Si está marcado, la opción de Factura se activará automáticamente al pagar saldos pendientes en el TPV.'
    )
