# -*- coding: utf-8 -*-
"""
Created on 2025-12-05 16:17:28

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MaintenanceTypeProblem(models.Model):
    _name = 'maintenance.type.problem'
    _description = 'Tipo de problema'

    name = fields.Char(
        string='Nombre')
