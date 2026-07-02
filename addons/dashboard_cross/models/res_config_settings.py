from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dashboard_cross_lost_customer_days = fields.Integer(
        string='Días para considerar Cliente Perdido',
        config_parameter='dashboard_cross.lost_customer_days',
        default=90,
        help="Número de días inactivos desde la última compra para que un cliente sea contabilizado como 'Perdido' en el tablero comercial."
    )
