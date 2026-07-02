# -*- coding: utf-8 -*-
"""
Created on 2026-01-07 10:41:56

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    supplier_stamping_ids = fields.One2many(
        'account.supplier.stamping', 'partner_id', string='Timbrados')
    is_electronic_invoicing = fields.Boolean(
        string='¿Es facturador electrónico?', compute='_compute_is_electronic_invoicing', store=True)

    @api.depends('supplier_stamping_ids.is_electronic_invoice_stamp')
    def _compute_is_electronic_invoicing(self):
        for record in self:
            record.is_electronic_invoicing = any(stamp.is_electronic_invoice_stamp for stamp in record.supplier_stamping_ids)
