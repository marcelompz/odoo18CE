# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:17:34

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCountryInherit(models.Model):
    _inherit = 'res.country'
    
    code_alfa_3 = fields.Char(
        string='Código alfa 3', store=True, tracking=True)
    code_numeric = fields.Char(
        string='Código numérico', store=True, tracking=True)


class ResPartnerOpeType(models.Model):
    _name = 'res.partner.ope.type'
    _description = 'Tipo de operación'
    
    operation_id = fields.Integer(
        string='ID de operación')
    name = fields.Char(
        string='Tipo de operación')
    operation_description = fields.Char(
        string='Descripción de la operación')
    

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    ncm = fields.Char(
        string='NCM', help='Nomenclatura común del Mercosur, debe tener entre 6 y 8 caracteres de longitud.', size=8, tracking=True)

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code


class ResDeliveryNote(models.Model):
    _name = 'res.delivery.note'
    _description = 'Motivo de la emisión'

    name = fields.Char(
        string='Motivo del problema')
    code = fields.Integer(
        string='Código')


class ResDeliveryResponsible(models.Model):
    _name = 'res.delivery.responsible'
    _description = 'Responsable de la emisión'

    name = fields.Char(
        string='Responsable de la emisión')
    code = fields.Integer(
        string='Código')


class FleetVehicleInherit(models.Model):
    _inherit = 'fleet.vehicle'

    _modality = [('1','Terrestre'),('2','Fluvial'),('3','Aéreo'),('4','Multimodal')]
    _type_id_vehicle = [('1', 'Número de identificación del vehículo'),('2', 'Número de matrícula del vehículo')]

    transport_type = fields.Selection(
        string='Tipo de transporte', selection=[('1', 'Propio'),('2','Tercero')], default='1', tracking=True)
    modality = fields.Selection(
        string='Modalidad', selection=_modality, default='1', tracking=True)
    type_of_transport_id = fields.Many2one(
        'res.transport.type', string='Tipo de transporte', help='Debe ser según el atributo de modalidad', tracking=True)
    type_id_vehicle = fields.Selection(
        string='Tipo de identificación del vehículo', 
        selection=_type_id_vehicle, default='2', tracking=True)
    cross_carrier_id = fields.Many2one(
        'res.partner', string='Transportadora', tracking=True)


class ResNegotiationCondition(models.Model):
    _name = 'res.negotiation.condition'
    _description = 'Condición de la negociación'

    code = fields.Char(
        string='Código')
    name = fields.Char(
        string='Nombre')


class ResTransportType(models.Model):
    _name = 'res.transport.type'
    _description = 'Tipo de transporte'

    name = fields.Char(
        string='Tipo de transporte')


class ResCreditDebitNote(models.Model):
    _name = 'res.credit.debit.note'
    _description = 'Motivo de la nota de crédito/débito'

    name = fields.Char(
        string='Motivo del problema')
    code = fields.Integer(
        string='Código')


class ResDocumentFormat(models.Model):
    _name = 'res.document.format'
    _description = 'Formato de documento para el DE'

    code = fields.Integer(
        string='Código')
    name = fields.Char(
        string='Nombre')


class ResDocumentFormatType(models.Model):
    _name = 'res.document.format.type'
    _description = 'Tipo de formato de documento para el DE'

    code = fields.Integer(
        string='Código')
    name = fields.Char(
        string='Nombre')


class ResPresence(models.Model):
    _name = 'res.presence'
    _description = 'Indicador de presencia'

    name = fields.Char(
        string='Nombre')
    presence_id = fields.Integer(
        string='ID de presencia')
