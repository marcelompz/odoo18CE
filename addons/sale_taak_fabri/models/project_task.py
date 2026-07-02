from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta')
    product_category_id = fields.Many2one('product.category', string='Categoría de Producto')
    sale_order_task_count = fields.Integer(
        string='Tareas Relacionadas a la Orden',
        compute='_compute_sale_order_task_count',
        store=False
    )

    @api.depends('sale_order_id')
    def _compute_sale_order_task_count(self):
        for task in self:
            if task.sale_order_id:
                task.sale_order_task_count = self.env['project.task'].search_count([
                    ('sale_order_id', '=', task.sale_order_id.id)
                ])
            else:
                task.sale_order_task_count = 0 