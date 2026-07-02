from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_category_id = fields.Many2one(
        'product.category',
        string='Categoría de Producto',
        related='product_id.categ_id',
        store=True,
        readonly=True,
        index=True,
        help='Categoría del producto asociada a la línea de venta'
    )

    order_date = fields.Datetime(
        string='Fecha de Orden',
        related='order_id.date_order',
        store=True,
        readonly=True,
        index=True,
        help='Fecha del pedido de venta'
    )

    validity_date = fields.Date(
        string='Fecha de Vencimiento',
        related='order_id.validity_date',
        store=True,
        readonly=True,
        index=True,
        help='Fecha de vencimiento del pedido de venta'
    )

    order_number = fields.Char(
        string='Número de Orden',
        related='order_id.name',
        store=True,
        readonly=True,
        index=True,
        help='Número del pedido de venta'
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Vendedor',
        related='order_id.user_id',
        store=True,
        readonly=True,
        index=True,
        help='Vendedor asignado al pedido'
    )

    order_customer = fields.Char(
        string='Orden-Cliente',
        compute='_compute_order_customer',
        store=True,
        index=True,
        help='Número de orden y nombre del cliente'
    )

    order_state = fields.Selection(
        string='Estado de Venta',
        related='order_id.state',
        store=True,
        readonly=True,
        index=True,
        help='Estado del pedido de venta'
    )

    mostrar_en_reportes = fields.Boolean(
        string='Mostrar en Cronograma',
        related='order_id.mostrar_en_reportes',
        store=True,
        readonly=True,
        index=True,
        help='Indica si la orden debe aparecer en los reportes'
    )

    @api.depends('order_id.name', 'order_id.partner_id.name', 'order_id.user_id.name')
    def _compute_order_customer(self):
        for line in self:
            line.order_customer = f"{line.order_id.name}-{line.order_id.partner_id.name}-{line.order_id.user_id.name}" 