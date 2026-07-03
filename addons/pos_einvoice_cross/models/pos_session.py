# -*- coding: utf-8 -*-
"""
Created on 2025-01-16 22:07:58

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PosSessionInherit(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
       """load the data to the pos.config.models"""
       data = super()._load_pos_data_models(config_id)
       data += ['res.country.state.district.city','l10n_latam.identification.type']
       return data
