# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    cross_group_products_normal_invoice = fields.Boolean(
        string="Agrupar productos en facturas normales",
        default=False
    )
    cross_group_products_export_invoice = fields.Boolean(
        string="Agrupar productos en facturas de exportacion",
        default=False
    )
