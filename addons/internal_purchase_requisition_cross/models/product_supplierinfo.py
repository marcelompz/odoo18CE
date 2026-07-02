# -*- coding: utf-8 -*-
"""
Created on 2025-12-03 13:26:11

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductSupplierinfoInherit(models.Model):
    _inherit = 'product.supplierinfo'

    product_length = fields.Float(
        string='Largo (Mts.)', digits='Product Unit of Measure')
    product_width = fields.Float(
        string='Ancho (Mts.)', digits='Product Unit of Measure')
    product_grammar = fields.Float(
        string='Gramatura (Grs.)', digits='Product Unit of Measure')
    price_meter = fields.Float(
        string='Precio x Mts.', digits='Product Price')
    apply_weight_product_related = fields.Boolean(
        related='product_tmpl_id.apply_weight_product', store=False)

    @api.onchange('product_grammar', 'price_meter')
    def _onchange_product_grammar_price_meter(self):
        if self.product_grammar and self.price_meter:
            self.price = 1000 * (self.price_meter / self.product_grammar)

    @api.constrains('product_width', 'product_grammar', 'price_meter', 'product_tmpl_id')
    def _check_technical_fields_required(self):
        """ Valida reglas de negocio al guardar una línea de proveedor individual """
        for record in self:
            # Usamos el campo related o accedemos directo al template
            if record.product_tmpl_id.apply_weight_product:
                # Verificamos si alguno es 0.0 (Float vacío es 0.0 en Odoo)
                if not record.product_width or not record.product_grammar or not record.price_meter:
                    raise ValidationError(_(
                        "Para el producto '%s', es obligatorio definir Ancho, Gramatura y Precio x Mts en la tarifa del proveedor."
                    ) % record.product_tmpl_id.name)
