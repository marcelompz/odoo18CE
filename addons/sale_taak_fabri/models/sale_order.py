from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    task_ids = fields.One2many('project.task', 'sale_order_id', string='Tareas Generadas')
    has_generated_tasks = fields.Boolean(
        string='Tiene Tareas Generadas',
        compute='_compute_has_generated_tasks',
        store=True
    )
    task_count = fields.Integer(
        string='Cantidad de Tareas',
        compute='_compute_task_count',
        store=False
    )

    @api.depends('task_ids')
    def _compute_has_generated_tasks(self):
        for order in self:
            order.has_generated_tasks = bool(order.task_ids)

    @api.depends('task_ids')
    def _compute_task_count(self):
        for order in self:
            order.task_count = len(order.task_ids)

    def action_open_task_generator(self):
        self.ensure_one()
        return {
            'name': 'Generador de Tareas',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.task.generator.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }

    def action_open_tasks(self):
        self.ensure_one()
        action = self.env.ref('sale_taak_fabri.action_sale_order_tasks').read()[0]
        action.update({
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_project_id': self.project_id.id if self.project_id else False,
            },
        })
        return action 