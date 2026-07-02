# -*- coding: utf-8 -*-
"""
Created on 2025-12-04 22:19:20

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTeamInherit(models.Model):
    _inherit = 'helpdesk.team'
    
    property_res_users_id = fields.Many2one(
        'res.users', string='Asignado a')
    equipment_ids = fields.Many2many(
        'maintenance.equipment', string='Maquinarias Vinculadas')
