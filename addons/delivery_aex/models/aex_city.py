# -*- coding: utf-8 -*-
"""
Created on 2025-06-30 21:03:32

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AexCity(models.Model):
    _name = 'aex.city'
    _description = 'AEX City'
    _order = 'name'

    name = fields.Char(
        string='City Name', required=True, index=True)
    code = fields.Char(
        string='AEX Code', required=True, index=True)
    department_name = fields.Char(
        string='Department Name')
    department_code = fields.Char(
        string='Department Code')
    country_name = fields.Char(
        string='Country Name')
    country_code = fields.Char(
        string='Country Code')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The AEX city code must be unique!')
    ]
    
    def name_get(self):
        result = []
        for city in self:
            name = f"[{city.code}] {city.name}"
            if city.department_name:
                name += f" ({city.department_name})"
            result.append((city.id, name))
        return result
        

class ResPartner(models.Model):
    _inherit = 'res.partner'

    aex_city_id = fields.Many2one(
        'aex.city',
        string='AEX City',
        domain="[('country_code', '=', partner_country_code)]",
        help="City as defined by AEX for shipping calculations. Required for AEX deliveries."
    )
    # Campo computado para ayudar al domain del M2O
    partner_country_code = fields.Char(
        compute='_compute_partner_country_code',
        string='Partner Country Code (AEX)'
    )
    
    @api.depends('country_id')
    def _compute_partner_country_code(self):
        # AEX usa 'PY' para Paraguay. Ajusta si es necesario.
        for partner in self:
            if partner.country_id and partner.country_id.code == 'PY':
                 partner.partner_country_code = 'PY'
            else:
                 partner.partner_country_code = False
