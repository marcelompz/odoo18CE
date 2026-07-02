# -*- coding: utf-8 -*-
"""
Created on 2025-06-30 21:08:10

@author: drojo
"""
# python
import requests

# odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AexCityImportWizard(models.TransientModel):
    _name = 'aex.city.import.wizard'
    _description = 'AEX City Import Wizard'

    def action_import_cities(self):
        """
        Connects to AEX API to fetch and update the city list.
        This should be called from a button on the wizard.
        """
        # Necesitamos un carrier de AEX para obtener las credenciales y la URL
        aex_carrier = self.env['delivery.carrier'].search([('delivery_type', '=', 'aex')], limit=1)
        if not aex_carrier:
            raise UserError(_("No AEX delivery carrier found. Please configure one first."))

        # 1. Obtener token de autorización
        try:
            token = aex_carrier._aex_get_authorization_token()
        except UserError as e:
            raise UserError(_("Could not get AEX authorization token. Error: %s", e))

        # 2. Llamar al endpoint de ciudades
        url = aex_carrier._aex_get_api_url() + 'envios/ciudades'
        payload = {
            'clave_publica': aex_carrier.aex_clave_publica,
            'codigo_autorizacion': token,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not connect to AEX Cities API. Error: %s") % e)

        if data.get('codigo') != 0 or 'datos' not in data:
            raise UserError(_("AEX API returned an error: %s") % data.get('mensaje', 'Unknown error'))
        
        cities_data = data['datos']
        if not cities_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('AEX City Import'),
                    'message': _('No cities were returned by the API.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }

        AexCity = self.env['aex.city']
        created_count = 0
        updated_count = 0
        
        for city_info in cities_data:
            vals = {
                'code': city_info.get('codigo_ciudad'),
                'name': city_info.get('denominacion'),
                'department_code': city_info.get('codigo_departamento'),
                'department_name': city_info.get('departamento_denominacion'),
                'country_code': city_info.get('codigo_pais'),
                'country_name': city_info.get('pais_denominacion'),
            }
            
            existing_city = AexCity.search([('code', '=', vals['code'])], limit=1)
            if existing_city:
                existing_city.write(vals)
                updated_count += 1
            else:
                AexCity.create(vals)
                created_count += 1
        
        message = _("%s cities created, %s cities updated.") % (created_count, updated_count)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('AEX City Import Successful'),
                'message': message,
                'sticky': False,
                'type': 'success',
            }
        }
