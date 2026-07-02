# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cross_group_products_normal_invoice = fields.Boolean(
        related='company_id.cross_group_products_normal_invoice',
        readonly=False
    )
    cross_group_products_export_invoice = fields.Boolean(
        related='company_id.cross_group_products_export_invoice',
        readonly=False
    )
