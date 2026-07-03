# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:30:44

@author: drojo
"""
# python 
import requests
import logging
import psycopg2
from psycopg2 import sql, OperationalError

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

def get_contribuyente_by_ruc(ruc_number):
    """
    Consulta la API externa turuc.com.py para obtener datos de un contribuyente por su RUC.

    :param ruc_number: Número de RUC a consultar (ej. '80120640-5').
    :type ruc_number: str
    :return: Diccionario con los datos del contribuyente si la consulta es exitosa,
            o None si no se encuentra o hay un error.
    :rtype: dict or None
    :raises requests.exceptions.RequestException: Si hay un problema de red o HTTP.
    :raises ValueError: Si la respuesta JSON no es válida.
    """
    if not ruc_number:
        return None

    api_url = f"https://turuc.com.py/api/contribuyente?ruc={ruc_number}"
    headers = {
        'accept': 'application/json'
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=10) # Añadir timeout para evitar esperas infinitas
        response.raise_for_status()  # Lanza una excepción para errores HTTP (4xx o 5xx)

        data = response.json()

        # Verificar si la API devuelve 'data' y si 'data' no es None o vacío
        if data and data.get('data'):
            return data.get('data')
        else:
            _logger.info("API externa (turuc.com.py) no encontró datos para el RUC %s: %s", ruc_number, data.get('message', 'Sin mensaje.'))
            return None # No se encontraron datos para el RUC
    except requests.exceptions.HTTPError as http_e:
        # Captura errores HTTP específicos (como 400 Bad Request, 404 Not Found, etc.)
        _logger.warning("Error HTTP al consultar la API turuc.com.py para RUC %s (Status: %s): %s",
                        ruc_number, http_e.response.status_code, http_e)
        try:
            error_data = http_e.response.json()
            api_message = error_data.get('message', '')
            if "No se encontraron registros con el ruc proveido" in api_message:
                _logger.info("RUC %s no encontrado por la API externa: '%s'", ruc_number, api_message)
                return None # Devolver None para el caso de "no encontrado"
            else:
                # Si es otro tipo de error HTTP o un mensaje inesperado, se eleva UserError
                raise UserError(_("Falla en la conexión con la base de datos de consulta. Detalle: %s") % api_message)
        except ValueError:
            # Error al decodificar JSON en caso de una respuesta de error no JSON
            raise UserError(_("La API externa devolvió un error HTTP %s con una respuesta no JSON válida para RUC %s.") % (http_e.response.status_code, ruc_number))
        
    except requests.exceptions.Timeout:
        _logger.error("Timeout al consultar la API turuc.com.py para RUC %s", ruc_number)
        raise UserError(_("Error de conexión con la base de datos externa: Tiempo de espera agotado."))
    
    except requests.exceptions.ConnectionError:
        _logger.error("Error de conexión de red al consultar la API turuc.com.py para RUC %s", ruc_number)
        raise UserError(_("Error de conexión de red con la base de datos externa. Verifique su conexión a Internet."))
        
    except requests.exceptions.RequestException as e:
        # Captura cualquier otro error de requests (problemas de red generales, etc.)
        _logger.error("Error inesperado de requests al consultar la API turuc.com.py para RUC %s: %s", ruc_number, e)
        raise UserError(_("Falla en la conexión con la base de datos de consulta. Detalle: %s") % e)
    
    except ValueError as e: # Catch JSON decoding errors for successful responses
        _logger.error("Error al decodificar la respuesta JSON de la API turuc.com.py para RUC %s: %s", ruc_number, e)
        raise UserError(_("La respuesta de la base de datos externa no es válida. Detalle: %s") % e)
    
    except Exception as e:
        # Captura cualquier otra excepción inesperada
        _logger.error("Error inesperado al consultar la API turuc.com.py para RUC %s: %s", ruc_number, e)
        raise UserError(_("Ocurrió un error inesperado al consultar la base de datos externa."))


class ResParterInherit(models.Model):
    _inherit = 'res.partner'
    
    operation_type_id = fields.Many2one(
        'res.partner.ope.type', string='Tipo de operación', tracking=True)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
    
        context = self._context
        # Valida si el campo 'name' cumple con el formato de RUC para realizar la búsqueda y reemplazar el nombre
        if context.get('default_name') and self._validate_ruc_py_format(context['default_name']):
            vat = context['default_name']
            consult = self._search_customer_by_ruc(ruc=vat)

            if consult is not None:
                name = consult.get('name', self.name)
    
            else:
                name = self.name

            copy_data = {
                'name': name,
                'vat': vat,
            }
            res.update(copy_data)
    
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('payment_term_id'):
                payment_term = self.env['account.payment.term'].search(
                    [('is_cash_payment', '=', True)],   
                    limit=1, 
                    order='id desc'
                )
                if payment_term:
                    vals['property_payment_term_id'] = payment_term.id

            if vals.get('vat'):
                res_vat = self._validate_ruc_py_format(value=vals.get('vat'))
                if res_vat:
                    consult = self._search_customer_by_ruc(ruc=vals['vat'])

                    if consult is not None:
                        vals['vat'] = consult.get('vat', False)
                        vals['name'] = consult.get('name', vals['name'])

            # Valida si el campo 'name' cumple con el formato de RUC para realizar la búsqueda y reemplazar el nombre
            if vals.get('name'):
                res_name = self._validate_ruc_py_format(value=vals.get('name'))
                if res_name:
                    consult = self._search_customer_by_ruc(ruc=vals['name'])

                    if consult is not None:
                        vals['vat'] = consult.get('vat', False)
                        vals['name'] = consult.get('name', vals['name'])
    
        return super().create(vals_list)

    @api.onchange('vat')
    def onchange_vat_cross(self):
        if not self.vat:
            return

        # Validar el formato del RUC
        if self.l10n_latam_identification_type_id.is_vat and not self._validate_ruc_py_format(self.vat):
            return      

        # Si todas las condiciones se cumplen, copiar el valor de vat a name
        res = self._search_customer_by_ruc(ruc=self.vat)

        if res is not None:
            self.name = res.get('name', self.name)
        
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Razón social %s encontrada desde el RUC %s') % (self.name, self.vat),
                    'type': 'success',
                    'sticky': False,
                },
            }

    def _validate_ruc_py_format(self, value):
        """
        Valida el RUC paraguayo ingresado.
        Formato esperado: NNNNNN-D o NNNNNNNN-D
        Donde N es un dígito y D es el dígito verificador.

        :param value: RUC a validar.
        :type value: str
        :return: True si el RUC es válido, False en caso contrario.
        :rtype: bool
        """
        if not value:
            return False

        vat_value = value.strip() # Quitar espacios al inicio/final por si acaso

        # 1. Verificar si tiene como separador el '-'
        if '-' not in vat_value:
            return False # No cumple, no hacer nada

        # Intentar dividir por el guion. Usamos maxsplit=1 por si hay más de un guion.
        parts = vat_value.split('-', 1)

        # Verificar que se dividió en exactamente dos partes
        if len(parts) != 2:
            return False # Formato incorrecto, no hacer nada

        part1, part2 = parts

        # 2. Verificar si la parte anterior al '-' tiene más de 5 dígitos y menos de 9 dígitos
        # Es decir, longitud 6 o 8.
        # Adicionalmente, podríamos verificar si son solo dígitos con part1.isdigit()
        if not (5 < len(part1) < 9): # len(part1) debe ser 6 o 7
            return False # No cumple, no hacer nada

        # 3. Verificar si la parte posterior al '-' tiene un solo dígito
        # Adicionalmente, podríamos verificar si es solo un dígito con part2.isdigit()
        if len(part2) != 1:
            return False # No cumple, no hacer nada

        # 4. Verificar que ambas partes sean solo dígitos (común para RUC/VAT)
        if not part1.isdigit() or not part2.isdigit():
            return False

        return True # Cumple con todas las condiciones

    def _search_customer_by_ruc(self, ruc):
        """
        Busca un cliente por su RUC.

        Si el RUC no existe, intenta obtener los datos del cliente desde una API externa.

        :param ruc: RUC (ID fiscal) del cliente.
        :type ruc: str
        :return: Diccionario con datos del cliente o un mensaje de error.
        :rtype: dict
        :raises UserError: Si el RUC no es válido o ya está registrado.
        """
        if not ruc:
            raise UserError(_('Debes ingresar el R.U.C. del cliente'))

        ruc = ruc.translate(str.maketrans('', '', '., /[]*(){}'))
        parts = ruc.split('-')
        ruc_dv = '#'

        if len(parts) == 1:
            ruc_dv = f"{ruc}-{self._get_verification_digit(ruc)}"
        elif len(parts) == 2:
            ruc_dv = f"{parts[0]}-{self._get_verification_digit(parts[0])}"
        elif len(parts) > 2:
            _logger.warning("Malformed RUC: %s", ruc)
            return {'error': _('Mal formato del número de documento.')}

        partners = self.env['res.partner'].search([
            '|', ('vat', '=', ruc), ('vat', '=', ruc_dv)
        ])

        if partners:
            partner_names = ', '.join(partners.mapped('name'))
            return {'error': _('Número de documento ya registrado con el cliente %s' % partner_names)}

        if ruc_dv != '#': ruc = ruc_dv

        if self.env.company.ruc_query_base_api == 'own':

            params = self.env.company._get_postgre_configurator()
            try:
                # Establecer conexión con PostgreSQL
                with psycopg2.connect(
                    dbname=params['postgre_dbname'], 
                    user=params['postgre_user'], 
                    password=params['postgre_password'], 
                    host=params['postgre_host'], 
                    port=params['postgre_port']
                ) as conn:
                    with conn.cursor() as cur:
                        # Usar consulta parametrizada para evitar inyección SQL
                        query = sql.SQL("SELECT id, name, vat, status FROM public.res_partner WHERE vat = %s")
                        cur.execute(query, (ruc,))
                        columnas = [desc[0] for desc in cur.description]  # Obtener nombres de columnas
                        filas = cur.fetchall()


                        # Transformar filas en lista de diccionarios
                        resultados = [dict(zip(columnas, fila)) for fila in filas]

                        return resultados[0]

            # Retorno del error
            except OperationalError as e:
                return {'error': _('Problema de conexión a la base de datos %s' % e)}

            except psycopg2.Error as e:
                return {'error': _('Error al ejecutar la consulta SQL - %s' % e)}

            except Exception as e:
                _logger.info(f'''
                    ERROR: {e}
                ''')
                return {'error': e}

        else:
            res = get_contribuyente_by_ruc(ruc)

            return {
                'id': res.get('doc'),
                'name': res.get('razonSocial'),
                'vat': res.get('ruc'),
                'status': res.get('estado'),
            }

    def _get_verification_digit(self, ruc):
        """
        Calculates the verification digit for a given RUC.

        :param ruc: RUC to verify.
        :type ruc: str
        :return: Verification digit.
        :rtype: int
        """
        total = sum(int(digit) * (base if (base := 2 + i % 9) else 2) for i, digit in enumerate(reversed(ruc)))
        return 0 if total % 11 in (0, 1) else 11 - total % 11
