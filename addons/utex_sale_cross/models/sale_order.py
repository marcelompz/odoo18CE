# -*- coding: utf-8 -*-
"""
Created on 2026-03-04 10:22:47

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    invoice_numbers_display = fields.Char(
        string='Nro. Factura', compute='_compute_invoice_numbers_display', store=True)
    total_qty_delivered = fields.Float(
        string='Total Entregado', compute='_compute_total_quantities', store=True, digits='Product Unit of Measure')
    total_qty_invoiced = fields.Float(
        string='Total Facturado', compute='_compute_total_quantities', store=True, digits='Product Unit of Measure')

    @api.depends('order_line.qty_delivered', 'order_line.qty_invoiced')
    def _compute_total_quantities(self):
        for order in self:
            # Sumamos las cantidades de todas las líneas de producto (ignorando secciones y notas)
            lines = order.order_line.filtered(lambda l: not l.display_type)
            order.total_qty_delivered = sum(lines.mapped('qty_delivered'))
            order.total_qty_invoiced = sum(lines.mapped('qty_invoiced'))

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.name', 'invoice_ids.invoice_number')
    def _compute_invoice_numbers_display(self):
        for order in self:
            # Filtramos facturas publicadas y que sean de cliente
            valid_invoices = order.invoice_ids.filtered(
                lambda m: m.state == 'posted' and m.move_type == 'out_invoice'
            )
            
            # Lógica: Usar invoice_number si tiene valor, sino usar name
            names = []
            for inv in valid_invoices:
                num = inv.invoice_number or inv.name

                if num:
                    names.append(num)
            
            # Unimos los números con comas (por si hay más de una factura)
            order.invoice_numbers_display = ", ".join(names) if names else ""
