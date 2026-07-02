# -*- coding: utf-8 -*-
"""
Created on 2025-06-16 13:30:54

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    configure_product_display_name = fields.Boolean(
        string='Configurar el nombre a ser mostrado del producto')


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'
    
    configure_product_display_name = fields.Boolean(
        related='company_id.configure_product_display_name', readonly=False)
