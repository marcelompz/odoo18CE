# -*- coding: utf-8 -*-
"""
Created on 2025-12-03 15:20:32

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    requisition_ids = fields.Many2many(
        'purchase.requisition', string='Requisiciones de Origen', copy=False)

    @api.onchange('partner_id')
    def _onchange_partner_id_update_specs(self):
        for line in self.order_line:
            if line.product_id and line.apply_weight_product and self.partner_id:
                supplier_info = self.env['product.supplierinfo'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                ], limit=1)

                if supplier_info:
                    line.product_width = supplier_info.product_width
                    line.product_grammar =  supplier_info.product_grammar
                    line.product_qty =  (line.product_length * supplier_info.product_grammar) / 1000
                    line.price_meter = supplier_info.price_meter

                else:
                    line.product_qty = 1.0
                    line.product_width = 0.0
                    line.product_grammar = 0.0
                    line.price_meter = 0.0
            else:
                    line.product_qty = 1.0
                    line.product_width = 0.0
                    line.product_grammar = 0.0
                    line.price_meter = 0.0
                    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribimos el create para detectar cuando se guarda una PO
        que viene de una o varias requisiciones.
        """
        orders = super(PurchaseOrderInherit, self).create(vals_list)

        for order in orders:
            if order.requisition_ids:
                reqs_to_update = order.requisition_ids.filtered(lambda r: r.approval_status != 'done')
                
                if reqs_to_update:
                    reqs_to_update.write({
                        'approval_status': 'done',
                        'purchase_order_id': order.id 
                    })
                    
                    # LOG (Opcional): Dejar un mensaje en el chatter de la requisición
                    # for req in reqs_to_update:
                    #     req.message_post(
                    #         body=f"Requisición finalizada. Se creó la Orden de Compra: <a href='#' data-oe-model='purchase.order' data-oe-id='{order.id}'>{order.name}</a>"
                    #     )
        
        return orders

        
class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    product_length = fields.Float(
        string='Largo (Mts.)', digits='Product Unit of Measure')
    product_width = fields.Float(
        string='Ancho (Mts.)', digits='Product Unit of Measure')
    product_grammar = fields.Float(
        string='Gramatura (Grs.)', digits='Product Unit of Measure')
    apply_weight_product = fields.Boolean(
        related='product_id.apply_weight_product')
    price_meter = fields.Float(
        string='Precio x Mts.', digits='Product Price')

    @api.onchange('product_id')
    def _onchange_product_get_specs(self):
        if not self.product_id or not self.order_id.partner_id:
            return

        if hasattr(self, '_onchange_product_id_price'):
            self._onchange_product_id_price()

        supplier_info = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.order_id.partner_id.id),
            ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)
        ], limit=1)

        if supplier_info and self.apply_weight_product:
            self.product_width = supplier_info.product_width
            self.product_grammar = supplier_info.product_grammar
            self.product_qty = (self.product_length * supplier_info.product_grammar) / 1000
            self.price_meter = supplier_info.price_meter

    def _prepare_stock_moves(self, picking):
        """
        Este método se ejecuta al confirmar la compra para preparar
        los datos de creación del stock.move
        """
        res = super(PurchaseOrderLineInherit, self)._prepare_stock_moves(picking)

        for move_vals in res:
            move_vals.update({
                'product_length': self.product_length,
                'product_width': self.product_width,
                'product_grammar': self.product_grammar,
            })

        return res
