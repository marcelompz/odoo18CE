# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 22:36:37

@author: drojo
"""
# python
import logging
import re

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
        string="Identification Type", index='btree_not_null', auto_join=True,
        default=lambda self: self.env.ref('l10n_py.it_vat', raise_if_not_found=False),
        help="The type of identification", tracking=True)
    partner_fantasy_name = fields.Char(
        string='Nombre fantasía', tracking=True)
    is_a_state_provider = fields.Boolean(
        string='Es proveedor del estado?', default=False, tracking=True)
    city_id = fields.Many2one(
        'res.country.state.district.city', string='Ciudad', tracking=True)
    house_number = fields.Float(
        string='Número de casa', default=0.0, tracking=True)

    district_id = fields.Many2one(
        related='city_id.district_id')
    state_id = fields.Many2one(
        'res.country.state', string='Departamento', ondelete='restrict', domain="[('country_id', '=?', country_id)]", tracking=True)
    country_id = fields.Many2one(
        'res.country', string='País', ondelete='restrict', store=True, tracking=True)
    partner_code = fields.Char(
        string='Código', default='/')
    client_eligible_de = fields.Boolean(
        string='Cliente elegible para facturación electrónica', compute='_compute_client_eligible_de')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'partner_code' not in vals or vals['partner_code'] == '/':
                vals['partner_code'] = self.env['ir.sequence'].next_by_code('res.partner') or '/'
        return super().create(vals_list)

    @api.onchange('city_id')
    def onchange_city_id(self):
        """is activated when identifying a change in the field city_id
        """
        self.state_id = self.city_id.district_id.state_id
        self.city = self.city_id.name
        
    @api.onchange('state_id')
    def onchange_state_id(self):
        """is activated when identifying a change in the field state_id
        """
        self.country_id = self.state_id.country_id

    @api.depends('l10n_latam_identification_type_id', 'vat', 'name', 'street', 'house_number', 'state_id', 'district_id', 'city_id', 'country_id', 'phone', 'email', 'partner_code')
    def _compute_client_eligible_de(self):
        for rec in self:
            mobile_val = getattr(rec, 'mobile', False)
            if rec.l10n_latam_identification_type_id and rec.vat and rec.name and rec.street and rec.house_number >= 0 and rec.state_id and rec.district_id and rec.city_id and rec.country_id and (rec.phone or mobile_val) and rec.email and rec.partner_code:
                rec.client_eligible_de = True
            else:
                rec.client_eligible_de = False

    def _is_valid_paraguayan_ci(self, ci_number):
        """
        Valida un número de Cédula de Identidad de Paraguay.
        La validación principal es que sea numérico y tenga una longitud aceptable.
        """
        if not ci_number.isdigit():
            return False
        
        # Una CI en Paraguay típicamente no supera los 8 millones.
        # Una longitud de 1 a 8 dígitos es una suposición razonable.
        if 1 <= len(ci_number) <= 8:
            return True
            
        return False

    def _is_valid_paraguayan_ruc(self, ruc_number):
        """
        Valida el número de RUC de Paraguay usando el algoritmo Módulo 11.
        Espera un formato como "NNNNNNN-D".
        """
        # El RUC debe contener un guion
        if '-' not in ruc_number:
            return False

        parts = ruc_number.split('-')
        if len(parts) != 2:
            return False

        body, check_digit_str = parts
        
        # El cuerpo y el dígito verificador deben ser numéricos
        if not body.isdigit() or not check_digit_str.isdigit():
            return False

        # El cuerpo del RUC puede ser la CI, así que usamos la misma validación de longitud
        if not (1 <= len(body) <= 8):
            return False

        check_digit = int(check_digit_str)

        # Algoritmo Módulo 11
        try:
            total = 0
            k = 2
            for digit in reversed(body):
                total += int(digit) * k
                k += 1
                if k > 9:
                    k = 2
            
            residuo = total % 11
            
            calculated_check_digit = (11 - residuo) if residuo > 1 else 0
            
            return check_digit == calculated_check_digit

        except (ValueError, TypeError):
            return False


    def check_vat_py(self, vat):
        """
        Valida el NIF de Paraguay, que puede ser un RUC (con dígito verificador)
        o una Cédula de Identidad (sin él).
        """
        vat = vat.strip()
        if '-' in vat:
            return self._is_valid_paraguayan_ruc(vat)
        else:
            # If Odoo stripped the hyphen, a RUC will be 9 digits long or more (body + 1 check digit)
            # CI is typically 1 to 8 digits. Let's try validating as RUC if we can split the last digit.
            if len(vat) > 8 and vat.isdigit():
                # Reconstruct hyphen format to use existing RUC validator
                reconstructed_vat = vat[:-1] + '-' + vat[-1]
                if self._is_valid_paraguayan_ruc(reconstructed_vat):
                    return True
            return self._is_valid_paraguayan_ci(vat)

    # Opcional pero recomendado: Mejorar el mensaje de error para ser más claro
    def _build_vat_error_message(self, country_code, wrong_vat, record_label):
        if country_code == 'py':
            return _(
                'El documento [%(wrong_vat)s] para %(record_label)s no parece ser una Cédula de Identidad o RUC válido. \n'
                'Nota: Ingrese la C.I. sin puntos (ej: 3958488) o el RUC con guion (ej: 80022393-3).',
                wrong_vat=wrong_vat, record_label=record_label
            )
        return super()._build_vat_error_message(country_code, wrong_vat, record_label)
