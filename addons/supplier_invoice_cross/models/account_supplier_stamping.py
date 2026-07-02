# -*- coding: utf-8 -*-
"""
Created on 2026-01-07 10:40:00

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountSupplierStamping(models.Model):
    _name = 'account.supplier.stamping'
    _description = 'Timbrado de Proveedor'
    _rec_name = 'name'

    name = fields.Char(
        string='Número de Timbrado', required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Proveedor', required=True)
    date_end = fields.Date(
        string='Fecha Vencimiento')
    is_electronic_invoice_stamp = fields.Boolean(
        string='Es timbrado para facturación electrónica', default=False)

    # Constraint para evitar duplicados por proveedor
    _sql_constraints = [
        ('unique_stamping_per_partner', 'unique(name, partner_id)', 
         'El número de timbrado debe ser único para este proveedor.')
    ]
