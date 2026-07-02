# -*- coding: utf-8 -*-
"""
Created on 2025-12-03 14:56:52

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    apply_weight_product = fields.Boolean(
        string='Aplica gramatura al producto?', default=False, tracking=True)

    @api.constrains('apply_weight_product', 'seller_ids')
    def _check_weight_product_requirements(self):
        """ Valida reglas de negocio al guardar el Producto """
        for product in self:
            
            if product.type == 'service':
                continue

            # Solo validamos si el check está activo
            if product.apply_weight_product:
                
                # 1. Validar que tenga al menos un proveedor
                if not product.seller_ids:
                    raise ValidationError(_(
                        "El producto '%s' tiene activa la gramatura, por lo tanto debe tener asignado al menos un Proveedor en la pestaña de Compras."
                    ) % product.name)

                # 2. Validar que todos los proveedores tengan los datos técnicos
                for seller in product.seller_ids:
                    if not all([seller.product_width, seller.product_grammar, seller.price_meter]):
                        raise ValidationError(_(
                            "El proveedor '%s' tiene datos incompletos (Largo, Ancho, Gramatura o Precio x Mts) "
                            "requeridos para productos con gramatura."
                        ) % seller.partner_id.name)
