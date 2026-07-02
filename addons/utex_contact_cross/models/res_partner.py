# -*- coding: utf-8 -*-
"""
Created on 2025-11-24 14:18:31

@author: drojo
"""
# python
from datetime import date
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    date_of_birth = fields.Date(
        string='Fecha de nacimiento')
    patient_age = fields.Char(
        string='Edad', compute='_compute_age')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for partner in self:
            if partner.date_of_birth:
                today = date.today()
                born = partner.date_of_birth
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                partner.patient_age = f'{age} años'
            else:
                partner.patient_age = 'No informada'
