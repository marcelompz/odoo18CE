# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 22:35:41

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    description = fields.Char(
        string='Descripción', help='Información de interés para Hacienda respecto al DE.')
    general_remarks = fields.Char(
        string='Observaciones', help='Información de interés para el emisor respecto de la DE. Puede ser cualquier información de marketing, publicidad, promociones, sorteos, etc., para el destinatario.')
    emitter_type = fields.Selection(
        string='Tipo de emisor', selection=[('1', 'Normal'),('2', 'Contingencia')], default='1')
    company_transactiontype_id = fields.Many2one(
        'res.company.transactiontype', string='Tipo de transacción de la empresa')
    company_taxtype_id = fields.Many2one(
        'res.company.taxtype', string='Tipo de impuesto de empresa')
    pos_customers_default_city_id = fields.Many2one(
        'res.country.state.district.city', string='Ciudad por defecto')

    def _localization_use_documents(self):
        """ Paraguayan localization use documents """
        self.ensure_one()
        return self.account_fiscal_country_id.code == "PY" or super()._localization_use_documents()


class ResCompanyTransactiontype(models.Model):
    _name = 'res.company.transactiontype'
    _description = 'Tipo de transacción de la empresa'

    name = fields.Char(
        string='Tipo de transacción')
    transaction_id = fields.Integer(
        string='ID de transacción')


class ResCompanyTaxtype(models.Model):
    _name = 'res.company.taxtype'
    _description = 'Tasa impositiva de la empresa'

    name = fields.Char(
        string='Tipo de impuesto de empresa')
    taxtype_id = fields.Integer(
        string='ID de tipo de impuesto')
