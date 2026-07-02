from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    sale_order_id = fields.Many2one(
        'sale.order',
        related='production_id.sale_order_id',
        store=False
    )
    sale_order_line_summary_html = fields.Html(
        string='Resumen de Productos de Pedido',
        compute='_compute_sale_order_line_summary_html',
        store=False
    )
    order_detail_line_ids = fields.Many2many(
        comodel_name='order.detail.lines',
        related='production_id.order_detail_line_ids',
        string='Líneas de Detalle',
        store=False
    )
    order_model_line_ids = fields.Many2many(
        comodel_name='order.detail.model.lines',
        related='production_id.order_model_line_ids',
        string='Líneas de Modelos',
        store=False
    )
    technical_info_ids = fields.Many2many(
        comodel_name='sale.order.technical.info',
        related='production_id.technical_info_ids',
        string='Información Técnica',
        store=False
    )

    @api.model
    def create(self, vals):
        # Asegurar que el nombre sea único por compañía
        if 'name' in vals and 'production_id' in vals:
            production = self.env['mrp.production'].browse(vals['production_id'])
            base_name = vals['name']
            counter = 1
            while True:
                # Buscar si ya existe una orden con el mismo nombre en la misma compañía
                existing = self.search([
                    ('name', '=', vals['name']),
                    ('company_id', '=', production.company_id.id)
                ])
                if not existing:
                    break
                vals['name'] = f"{base_name} ({counter})"
                counter += 1
        return super(MrpWorkorder, self).create(vals)

    def write(self, vals):
        # Asegurar que el nombre sea único por compañía al actualizar
        if 'name' in vals:
            for record in self:
                base_name = vals['name']
                counter = 1
                while True:
                    # Buscar si ya existe una orden con el mismo nombre en la misma compañía
                    existing = self.search([
                        ('name', '=', vals['name']),
                        ('company_id', '=', record.company_id.id),
                        ('id', '!=', record.id)
                    ])
                    if not existing:
                        break
                    vals['name'] = f"{base_name} ({counter})"
                    counter += 1
        return super(MrpWorkorder, self).write(vals)

    @api.depends('production_id.sale_order_id', 'production_id.sale_order_id.order_line')
    def _compute_sale_order_line_summary_html(self):
        for workorder in self:
            summary = {}
            sale_order = workorder.production_id.sale_order_id
            if sale_order and sale_order.order_line:
                for line in sale_order.order_line:
                    _logger.info(f"Workorder {workorder.id} - Producto: {line.product_id.display_name}, Cantidad: {line.product_uom_qty}")
                    key = line.product_id
                    summary.setdefault(key, 0)
                    summary[key] += line.product_uom_qty
            html = "<table class='table table-sm'><tr><th>Producto</th><th>Cantidad Total</th></tr>"
            for product in sorted(summary, key=lambda p: p.name):
                html += f"<tr><td>{product.display_name}</td><td>{summary[product]}</td></tr>"
            html += "</table>" if summary else "<i>No hay productos en el pedido</i>"
            workorder.sale_order_line_summary_html = html

    def action_toggle_state(self):
        for workorder in self:
            if workorder.state == 'pending':
                workorder.state = 'in_progress'
            elif workorder.state == 'in_progress':
                workorder.state = 'done'
            else:
                workorder.state = 'pending' 