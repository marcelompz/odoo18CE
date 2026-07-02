# -*- coding: utf-8 -*-
"""
Created on 2026-02-06 11:27:37

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    require_reference = fields.Boolean(string="Requiere Referencia/Nro Operación")

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.append('require_reference')
        return result
