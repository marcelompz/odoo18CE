# -*- coding: utf-8 -*-
"""
Created on 2025-11-28 11:10:53

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

    wave_source_location_id = fields.Many2one(
        'stock.location', string="Ubicación Origen (Ola Producción)", help="Ubicación por defecto desde donde sale el material (Ej. Almacén Principal)")
    wave_dest_location_id = fields.Many2one(
        'stock.location', string="Ubicación Destino (Ola Producción)", help="Ubicación por defecto a donde va el material (Ej. Corte, Confección)")
