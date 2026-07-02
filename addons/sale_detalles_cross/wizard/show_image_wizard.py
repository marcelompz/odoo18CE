# -*- coding: utf-8 -*-
"""
Created on 2025-06-10 13:29:41

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ShowImageWizard(models.TransientModel):
    _name = 'show.image.wizard'
    _description = 'Show Image Wizard'

    image = fields.Binary(
        string='Imagen')
