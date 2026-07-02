# -*- coding: utf-8 -*-
"""
Created on 2026-04-06 11:56:25

@author: drojo
"""
# python
import logging
import re

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    def _sync_barcode_from_default_code(self):
        """
        Extrae el número de secuencia del default_code y lo asigna al barcode.
        Ejemplo: MER-PER/4886-MUSP-STD-04 -> 4886
        """
        for product in self:
            if product.default_code and '/' in product.default_code:
                # Usamos una expresión regular para buscar los dígitos después de la barra /
                # Explicación: busca una '/' y captura todos los dígitos (\d+) que le siguen
                match = re.search(r'/(\d+)', product.default_code)
                if match:
                    sequence_number = match.group(1)
                    # Solo actualizamos si el barcode es diferente para evitar recursividad innecesaria
                    if product.barcode != sequence_number:
                        product.barcode = sequence_number

    @api.model_create_multi
    def create(self, vals_list):
        # Primero dejamos que el módulo base (sale_detalles) cree el producto y genere el default_code
        products = super().create(vals_list)
        # Luego ejecutamos nuestra lógica de extracción
        products._sync_barcode_from_default_code()
        return products

    def write(self, vals):
        # Ejecutamos el write original
        res = super().write(vals)
        # Si se modificó algo que dispara el cambio de default_code en el módulo base, sincronizamos
        if 'default_code' in vals or 'product_template_attribute_value_ids' in vals:
            self._sync_barcode_from_default_code()
        return res
