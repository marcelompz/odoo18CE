# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:18:32

@author: drojo
"""
#python
import psycopg2
from psycopg2 import OperationalError

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    url_api_cross = fields.Char()
    api_key_cross = fields.Char()
    sync_communication_cross = fields.Boolean()
    digital_certificate_expiration = fields.Date()
    without_discount_invoice = fields.Boolean()
    l10n_py_enabled_invoice_number = fields.Boolean()
    presence_id = fields.Many2one('res.presence')
    add_pos_electronic_invoice_functions = fields.Boolean()
    ruc_query_base_api = fields.Selection([('own', 'Propio'),('third', 'Tercero')], default='own')

    def verify_connection_res_partner_search_config(self):
        """
        Verifica si hay conexión con la base de datos PostgreSQL.

        Returns:
            str: Mensaje de éxito o error en la conexión.
        """
        params = self._get_postgre_configurator()

        try:
            # Establecer conexión con PostgreSQL
            with psycopg2.connect(
                dbname=params['postgre_dbname'],
                user=params['postgre_user'],
                password=params['postgre_password'],
                host=params['postgre_host'],
                port=params['postgre_port']
            ) as conn:

                # Conexión exitosa
                return True

        except OperationalError as e:
            return f"ERROR: Problema de conexión a la base de datos - {e}"

        except Exception as e:
            return f"ERROR: {e}"

    def _get_postgre_configurator(self):
        """
        Obtiene los valores de configuración para la conexión a PostgreSQL desde el modelo correspondinte.

        Returns:
            dict: Diccionario con los parámetros de conexión.
        """
        config = self.env['res.partner.search.config'].search([], limit=1)

        if not config:
            raise UserError(f'No se encontraron datos de configuración para probar la conexión.')

        return {
            'postgre_dbname': config.db_name,
            'postgre_user': config.db_user,
            'postgre_password': config.db_pwd,
            'postgre_host': config.db_host,
            'postgre_port': config.db_port,
        }
