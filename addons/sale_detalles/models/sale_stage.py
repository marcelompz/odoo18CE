from odoo import models, fields, api

class SaleStage(models.Model):
    _name = 'sale.stage'
    _description = 'Etapas de Venta'
    _order = 'sequence, id'

    name = fields.Char(string='Etapa de Venta', required=True, translate=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    description = fields.Text(string='Descripción', translate=True)
    color = fields.Integer(string='Color')
    fold = fields.Boolean(string='Plegado en Kanban', default=False)
    is_done = fields.Boolean(string='Es Etapa Final', default=False)
    is_cancel = fields.Boolean(string='Es Cancelación', default=False)

    def _get_default_stage(self):
        return self.search([('sequence', '=', 1)], limit=1) 