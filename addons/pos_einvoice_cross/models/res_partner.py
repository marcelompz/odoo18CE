# -*- coding: utf-8 -*-
"""
Created on 2025-02-24 12:30:06

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_fields(self, config_id):
       data = super()._load_pos_data_fields(config_id)
       data += ['client_eligible_de']
       return data
