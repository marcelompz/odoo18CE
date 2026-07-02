# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    company_signature = fields.Image(string="Signature", attachment=True)
