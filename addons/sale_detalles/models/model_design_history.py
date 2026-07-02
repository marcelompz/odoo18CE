from odoo import models, fields, api

class ModelDesignHistory(models.Model):
    _name = 'model.design.history'
    _description = 'Historial de Diseño'

    name = fields.Char(
        string='Nombre',
        required=True,
        compute='_compute_name',
        store=True,
        default="Nuevo Historial"
    )
    model_line_id = fields.Many2one(
        'order.detail.model.lines',
        string='Línea de Modelo',
        ondelete='cascade'
    )
    order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        required=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Vendedor',
        related='order_id.user_id',
        store=True,
        readonly=True
    )
    stage_id = fields.Many2one(
        'sale.stage',
        string='Estado de Venta',
        related='order_id.stage_id',
        store=True,
        readonly=True
    )
    model_type_id = fields.Many2one(
        'model.type',
        string='Modelo',
        required=False
    )
    designer_id = fields.Many2one(
        'res.users',
        string='Diseñador',
        required=True,
        default=lambda self: self.env.user
    )
    work_type = fields.Selection(
        selection=[
            ('new', 'Nuevo'),
            ('modification', 'Modificaciones')
        ],
        string='Tipo de Trabajo',
        required=True,
        default='new'
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    notes = fields.Text(
        string='Notas'
    )
    count = fields.Integer(
        string='Cantidad',
        default=1,
        store=True
    )

    @api.depends('order_id', 'model_type_id', 'designer_id', 'date')
    def _compute_name(self):
        for record in self:
            try:
                if record.order_id and record.designer_id and record.date:
                    if record.model_type_id:
                        record.name = f"{record.order_id.name} - {record.model_type_id.name} - {record.designer_id.name} - {record.date}"
                    else:
                        record.name = f"{record.order_id.name} - Sin Modelo - {record.designer_id.name} - {record.date}"
                else:
                    record.name = "Nuevo Historial"
            except Exception:
                record.name = "Nuevo Historial"

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'} 