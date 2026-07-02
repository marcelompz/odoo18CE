from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_categ_id = fields.Many2one(
        related='product_id.categ_id',
        string='Categoría de Producto',
        store=True,
        readonly=True
    )

    order_display_name = fields.Char(
        string='Pedido de Venta Detallado',
        compute='_compute_order_display_name',
        store=True
    )

    validity_date = fields.Date(
        string='Fecha de Vencimiento',
        related='order_id.validity_date',
        store=True
    )

    production_id = fields.Many2one(
        'mrp.production',
        string='Orden de Fabricación',
        compute='_compute_production_id',
        store=True
    )

    has_pending_tasks = fields.Boolean(
        string='Tiene Tareas Pendientes',
        compute='_compute_has_pending_tasks',
        store=True
    )

    task_status = fields.Char(
        string='Estado de Tareas',
        compute='_compute_task_status',
        store=False,
    )

    @api.depends('has_pending_tasks', 'production_id')
    def _compute_task_status(self):
        for line in self:
            if not line.production_id:
                line.task_status = 'N/A'
            elif line.has_pending_tasks:
                line.task_status = 'Pendiente'
            else:
                line.task_status = 'Completo'

    @api.depends('order_id.name')
    def _compute_production_id(self):
        for line in self:
            # Buscar la orden de producción relacionada con esta línea de venta
            production = self.env['mrp.production'].search([
                ('origin', 'like', f"{line.order_id.name}%")
            ], limit=1)
            line.production_id = production.id if production else False

    @api.depends('production_id.workorder_ids.state')
    def _compute_has_pending_tasks(self):
        for line in self:
            pending = False
            if line.production_id and line.production_id.workorder_ids:
                if any(wo.state not in ['done', 'cancel'] for wo in line.production_id.workorder_ids):
                    pending = True
            line.has_pending_tasks = pending

    @api.depends('order_id.name', 'order_id.client_order_ref', 'order_id.partner_id.name', 'order_id.user_id.name', 'production_id.workorder_ids.state')
    def _compute_order_display_name(self):
        for line in self:
            if line.order_id:
                ref = line.order_id.client_order_ref or ''
                cliente = line.order_id.partner_id.name or ''
                vendedor = line.order_id.user_id.name or ''
                nombre = line.order_id.name or ''
                
                display = f"{nombre}"
                if ref:
                    display += f" ({ref})"
                if cliente:
                    display += f" {cliente}"
                if vendedor:
                    display += f", {vendedor}"

                if line.production_id and line.production_id.workorder_ids:
                    completed_wos = line.production_id.workorder_ids.filtered(lambda wo: wo.state == 'done')
                    if completed_wos:
                        display += f" [Completado: {', '.join(completed_wos.mapped('name'))}]"

                line.order_display_name = display.strip()
            else:
                line.order_display_name = '' 