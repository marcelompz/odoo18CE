# -*- coding: utf-8 -*-
"""
Created on 2025-06-16 15:17:39

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class OrderDetailModelLines(models.Model):
    _inherit = 'order.detail.model.lines'

    def open_image_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ver Imagen',
            'res_model': 'show.image.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_image': self.image,
            }
        }
