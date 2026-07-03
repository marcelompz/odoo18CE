# -*- coding: utf-8 -*-
"""
Created on 2025-02-24 12:36:51

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCountryStateDistrictCityInherit(models.Model):
    _name = 'res.country.state.district.city'
    _inherit = ['res.country.state.district.city','pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
       return ['id', 'name']
