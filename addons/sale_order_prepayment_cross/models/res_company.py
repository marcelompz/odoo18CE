# -*- coding: utf-8 -*-
"""
Created on 2025-08-15 17:20:02

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

    prepayment_auto_reconcile = fields.Boolean(
        string='Conciliación automática de anticipos', 
        help='Conciliar automáticamente los anticipos con las facturas cuando se crean.', default=True)
    advance_approval_percentag = fields.Float(
        string='Porcentaje de aprobación de anticipos',
        help='Porcentaje mínimo de aprobación para anticipos. Si el monto del anticipo es mayor o igual a este porcentaje del total del pedido, se continúa el proceso.', default=0.5)
