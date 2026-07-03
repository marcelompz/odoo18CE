# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 22:33:56

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCountryStateInherit(models.Model):
    _inherit = 'res.country.state'
    
    district_ids = fields.One2many(
        'res.country.state.district', 'state_id', string='Distritos')


class ResCountryStateDistrict(models.Model):
    _name = 'res.country.state.district'
    _description = 'Distritos'
    
    name = fields.Char(string='Distrito', required=True)
    code = fields.Char(string='Código', required=True)
    state_id = fields.Many2one(
        'res.country.state',string='Departamento')
    city_ids = fields.One2many(
        'res.country.state.district.city', 'district_id', string='Ciudades')
    
    
class ResCountryStateDistrictCity(models.Model):
    _name = 'res.country.state.district.city'
    _description = 'Ciudades'

    name = fields.Char(string='Ciudad', required=True)
    code = fields.Char(string='Código', required=True)
    district_id = fields.Many2one(
        'res.country.state.district', string='Distrito')
    
    
class L10nLatamBaseInherit(models.Model):
    _inherit = 'l10n_latam.identification.type'

    document_id = fields.Integer(
        string='ID del documento')
    
    
class UomUomInherit(models.Model):
    _inherit = 'uom.uom'
    
    code = fields.Char(string='Código')
