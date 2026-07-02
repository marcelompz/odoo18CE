# -*- coding: utf-8 -*-
"""
Created on 2025-12-09 19:42:48

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResUsersInherit(models.Model):
    _inherit = 'res.users'
    
    helpdesk_allowed_partner_ids = fields.Many2many(
        'res.partner', string='Contactos Permitidos en Helpdesk')
