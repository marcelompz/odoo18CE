# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class SaleOrderPresupuestoLine(models.Model):
    _name = 'sale.order.presupuesto.line'
    _description = 'Línea Presupuesto Rápido (Pedido de Venta)'

    order_id = fields.Many2one(
        'sale.order',
        string='Pedido de venta',
        required=True,
        ondelete='cascade',
    )
    producto_comercial_id = fields.Many2one(
        'producto.comercial',
        string='Producto comercial',
        required=True,
        ondelete='restrict',
    )
    name = fields.Char(related='producto_comercial_id.name', readonly=True)
    quantity = fields.Float('Cantidad', digits='Product Unit of Measure', default=1.0, required=True)
    price_unit = fields.Float(
        'Precio unitario',
        digits='Product Price',
        related='producto_comercial_id.list_price',
        store=True,
        readonly=False,
    )
    price_subtotal = fields.Float('Subtotal', digits='Product Price', compute='_compute_price_subtotal', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('quantity', 'price_unit', 'producto_comercial_id')):
            self.mapped('order_id')._sync_presupuesto_order_line()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.mapped('order_id')._sync_presupuesto_order_line()
        return lines

    def unlink(self):
        orders = self.mapped('order_id')
        res = super().unlink()
        orders._sync_presupuesto_order_line()
        return res


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    presupuesto_rapido_line_ids = fields.One2many(
        'sale.order.presupuesto.line',
        'order_id',
        string='Presupuesto rápido',
        copy=False,
    )
    amount_presupuesto_rapido = fields.Float(
        'Total Presupuesto rápido',
        digits='Product Price',
        compute='_compute_amount_presupuesto_rapido',
        store=True,
    )
    other_note = fields.Html(
        string='Otras notas')

    @api.depends('presupuesto_rapido_line_ids.price_subtotal')
    def _compute_amount_presupuesto_rapido(self):
        for order in self:
            order.amount_presupuesto_rapido = sum(order.presupuesto_rapido_line_ids.mapped('price_subtotal'))

    def _get_report_lines(self):
        """Líneas para el reporte: order_line (sin producto Presupuesto) + presupuesto_rapido_line_ids."""
        self.ensure_one()
        product_presupuesto = self._get_producto_presupuesto()
        order_lines = self.order_line
        if product_presupuesto:
            order_lines = order_lines.filtered(lambda l: l.product_id != product_presupuesto)
        result = []
        for line in order_lines:
            result.append({
                'quantity': int(line.product_uom_qty),
                'name': (line.product_id.name if line.product_id else '') or line.name,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_total,
            })
        for line in self.presupuesto_rapido_line_ids:
            result.append({
                'quantity': int(line.quantity),
                'name': line.name or '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
            })
        return result

    def _get_producto_presupuesto(self):
        """Producto para cargar el total en una línea del pedido (configuración en Empresa o búsqueda por nombre)."""
        self.ensure_one()
        product = self.company_id.product_presupuesto_id
        if not product:
            product = self.env['product.product'].search(
                [('sale_ok', '=', True), ('name', 'ilike', 'presupuesto')],
                limit=1,
            )
        return product

    def _sync_presupuesto_order_line(self):
        """Crea o actualiza la línea del pedido con producto Presupuesto y el total del presupuesto rápido."""
        product_presupuesto = self._get_producto_presupuesto()
        if not product_presupuesto:
            return
        for order in self:
            amount = sum(order.presupuesto_rapido_line_ids.mapped('price_subtotal'))
            presupuesto_line = order.order_line.filtered(
                lambda l: l.product_id == product_presupuesto
            )
            if amount:
                if presupuesto_line:
                    presupuesto_line.write({
                        'product_uom_qty': 1.0,
                        'price_unit': amount,
                        'name': _('Presupuesto rápido'),
                    })
                else:
                    order.write({
                        'order_line': [(0, 0, {
                            'product_id': product_presupuesto.id,
                            'name': _('Presupuesto rápido'),
                            'product_uom_qty': 1.0,
                            'price_unit': amount,
                        })],
                    })
            else:
                if presupuesto_line:
                    presupuesto_line.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_presupuesto_order_line()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'presupuesto_rapido_line_ids' in vals or 'order_line' in vals:
            self._sync_presupuesto_order_line()
        return res
