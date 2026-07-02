from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_detail_line_id = fields.Many2one('order.detail.lines', string='Línea de Detalle', ondelete='cascade')
    product_number = fields.Integer(string='Número de Producto', help='Número del producto en la línea de detalle (1-5)')
    is_detail_line = fields.Boolean(string='Es Línea de Detalle', compute='_compute_is_detail_line', store=True)

    @api.depends('order_detail_line_id')
    def _compute_is_detail_line(self):
        for record in self:
            record.is_detail_line = bool(record.order_detail_line_id)

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        if self.is_detail_line and self.order_detail_line_id and self.order_detail_line_id.exists():
            # Usar with_context para prevenir recursión
            self.order_detail_line_id.with_context(skip_price_update_recursion=True)._update_price_from_sale_line()

    def write(self, vals):
        result = super(SaleOrderLine, self).write(vals)
        if self.is_detail_line and self.order_detail_line_id and self.order_detail_line_id.exists():
            if 'price_unit' in vals:
                # Usar with_context para prevenir recursión
                self.order_detail_line_id.with_context(skip_price_update_recursion=True)._update_price_from_sale_line()
        return result

    def unlink(self):
        for record in self:
            if record.order_detail_line_id and not self.env.context.get('bypass_detail_line_unlink'):
                # No borramos la línea de detalle aquí para evitar recursión
                pass
        return super(SaleOrderLine, self).unlink()

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    show_in_import_reference = fields.Boolean(string='Mostrar en importación de referencias', default=False) 