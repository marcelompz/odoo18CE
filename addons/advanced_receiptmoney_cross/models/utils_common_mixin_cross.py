# -*- coding: utf-8 -*-
"""
Created on 2025-07-29 13:06:03

@author: drojo
"""
# python
import pytz
from datetime import datetime

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class UtilsCommonMixinCross(models.AbstractModel):
    _name = 'utils.common.mixin.cross'
    _description = 'Mixin de Utilidades comunes'

    def get_current_datetime(self, option='datetime'):
        """Gets the current date or datetime in the user's timezone."""
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        user_time = fields.Datetime.context_timestamp(self, datetime.now())

        if option == 'date':
            return user_time.date()
        else:
            return user_time

    def check_installation(self, module_name):
        """Check if a module is installed"""
        return bool(self.env['ir.module.module'].sudo().search([
            ('name', '=', module_name), 
            ('state', '=', 'installed')
        ], limit=1))

    def check_field_exists(self, model_name, field_name):
        """Check if a field exists on a given model."""
        return field_name in self.env[model_name].fields_get()
