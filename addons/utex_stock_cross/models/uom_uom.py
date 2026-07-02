# -*- coding: utf-8 -*-
"""
Created on 2026-04-20 11:39:30

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class UomUomInherit(models.Model):
    _inherit = 'uom.uom'

    def write(self, vals):
        group_xml_id = 'utex_stock_cross.group_uom_editor'
        
        if not self.env.user.has_group(group_xml_id):
            fields_to_protect = ['name', 'factor', 'uom_type', 'category_id']
            if any(f in vals for f in fields_to_protect):
                raise AccessError(_(
                    "No tienes permisos para modificar Unidades de Medida existentes. "
                    "Solo un supervisor de Unidades de Medida puede realizar estos cambios."
                ))
        
        return super().write(vals)
