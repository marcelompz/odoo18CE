# -*- coding: utf-8 -*-
"""
Created on 2025-02-24 12:40:25

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class l10n_latamIdentificationTypeInherit(models.Model):
    _name = 'l10n_latam.identification.type'
    _inherit = ['l10n_latam.identification.type','pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
       return ['id', 'name']
