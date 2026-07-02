# -*- coding: utf-8 -*-
"""
Created on 2025-03-26 11:06:23

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils

_logger = logging.getLogger(__name__)


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()

        if res:
            if self.purchase_id.adjust_sale_price:
                for line in self.purchase_id.order_line:
                    # Verificación y actualización del margen de ganancia solo si ha cambiado
                    if line.product_margin_gain != line.product_id.product_tmpl_id.margin_gain:
                        line.product_id.product_tmpl_id.margin_gain = line.product_margin_gain

                    # Actualizar el precio de venta si el margen de ganancia es positivo
                    if line.product_margin_gain > 0.0:
                        line.product_id.product_tmpl_id.list_price = line.product_id.product_tmpl_id.standard_price * (1 + line.product_margin_gain)

        return res
