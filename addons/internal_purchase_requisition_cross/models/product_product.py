# -*- coding: utf-8 -*-
"""
Created on 2026-02-19 13:13:15

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    def action_open_product_form(self):
        self.ensure_one()
        return {
            'name': 'Editar Producto',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
