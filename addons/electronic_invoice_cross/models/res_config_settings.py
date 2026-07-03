# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:29:14

@author: drojo
"""
# python
import requests  # api
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


# --- Función para consultar la API externa ---
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
    except requests.exceptions.Timeout:
        _logger.error("Timeout al consultar la API turuc.com.py para RUC %s", ruc_number)
        raise UserError(_("Error de conexión con la base de datos externa: Tiempo de espera agotado."))
    except requests.exceptions.RequestException as e:
        _logger.error("Error al consultar la API turuc.com.py para RUC %s: %s", ruc_number, e)
        # Puedes añadir más detalles aquí, como response.status_code si response está disponible
        raise UserError(_("Falla en la conexión con la base de datos de consulta. Detalle: %s") % e)
    except ValueError as e: # Catch JSON decoding errors
        _logger.error("Error al decodificar la respuesta JSON de la API turuc.com.py para RUC %s: %s", ruc_number, e)
        raise UserError(_("La respuesta de la base de datos externa no es válida. Detalle: %s") % e)
    except Exception as e:
        _logger.error("Error inesperado al consultar la API turuc.com.py para RUC %s: %s", ruc_number, e)
        raise UserError(_("Ocurrió un error inesperado al consultar la base de datos externa."))

class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Company Configuration
    cross_fe_description = fields.Char(
        string='Descripción', related='company_id.description', help='Información de interés para Hacienda respecto al DE.', readonly=False, tracking=True)
    cross_fe_general_remarks = fields.Char(
        string='Observaciones', related='company_id.general_remarks', help='Información de interés para el emisor respecto del DE. Puede ser cualquier información de marketing, publicidad, promociones, sorteos, etc., para el destinatario.', readonly=False, tracking=True)
    cross_fe_emitter_type = fields.Selection(
        string='Tipo de emisor', related='company_id.emitter_type', selection=[('1', 'Normal'),('2', 'Contingencia')], default='1', readonly=False, tracking=True)
    cross_fe_company_transactiontype_id = fields.Many2one(
        string='Tipo de transacción de la empresa', related='company_id.company_transactiontype_id', readonly=False, tracking=True)
    cross_fe_company_taxtype_id = fields.Many2one(
        string='Tipo de impuesto de la empresa', related='company_id.company_taxtype_id', readonly=False, tracking=True)
    cross_fe_presence_id = fields.Many2one(
        string='Indicador de presencia', related='company_id.presence_id', readonly=False, tracking=True)
    l10n_py_enabled_invoice_number = fields.Boolean(
        string='Habilitar número de factura', related='company_id.l10n_py_enabled_invoice_number', readonly=False, tracking=True)
    # Conexion Configurator
    cross_fe_url_api = fields.Char(
        string='API URL', related='company_id.url_api_cross', help='Ex.: https://api.crossnexion.com/<tenantId>/', readonly=False, tracking=True)
    cross_fe_api_key = fields.Char(
        string='API Key', related='company_id.api_key_cross', readonly=False, tracking=True)
    cross_fe_sync_communication = fields.Boolean(
        string='Comunicación sincrónica', related='company_id.sync_communication_cross', readonly=False, tracking=True)
    cross_digital_certificate_expiration = fields.Date(
        string='Vencimiento del certificado digital', related='company_id.digital_certificate_expiration', readonly=False, tracking=True)
    # Sales
    without_discount_invoice = fields.Boolean(
        string='Llevar los descuentos en el monto al generar factura', related='company_id.without_discount_invoice', readonly=False, tracking=True)
    # POS
    module_pos_einvoice_cross = fields.Boolean(
        string='Factura electrónica desde el PdV', related='company_id.add_pos_electronic_invoice_functions', readonly=False, tracking=True)
    cross_pos_customers_default_city_id = fields.Many2one(
        string='Ciudad por defecto', related='company_id.pos_customers_default_city_id', readonly=False, tracking=True)
    cross_ruc_query_base_api = fields.Selection(
        string='Base de consulta', related='company_id.ruc_query_base_api', readonly=False, tracking=True)

    def check_connection_with_cross(self):
        # Validación de URL y API Key
        if not self.company_id.url_api_cross or not self.company_id.api_key_cross:
            raise UserError("Faltan datos de configuración. Verifique la URL y el API Key para la conexión.")
        
        url = f"{self.company_id.url_api_cross}/test"
        headers = {
            'Authorization': f'Bearer api_key_{self.company_id.api_key_cross}'
        }

        try:
            # Realizar solicitud GET
            response = requests.get(url=url, verify=False, headers=headers)
            response.raise_for_status()  # Genera una excepción si el código de estado no es 2xx

            # Conexión exitosa
            if response.status_code == 200:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': '¡Conexión exitosa con la interfaz de Crossnexion!',
                        'type': 'rainbow_man',
                    }
                }
        except requests.exceptions.RequestException as e:
            # Manejo de errores de conexión
            raise UserError(f"Error al conectar con la API: {str(e)}")

        # Error genérico en caso de código de estado inesperado
        raise UserError(f"Conexión fallida. Código de estado: {response.status_code}")

    def action_open_res_partner_search_config(self):
        # Buscar el único registro del modelo `res.partner.search.config`
        config = self.env['res.partner.search.config'].search([], limit=1)
        if not config:
            raise UserError("No se encontró ningún registro en la configuración.")
        
        # Devolver una acción para abrir la vista form en modo modal
        return {
            'name': 'Configuración de Búsqueda de Partner',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner.search.config',
            'view_mode': 'form',
            'res_id': config.id,
            'target': 'new',
        }

    def action_test_res_partner_search_config(self):
        self.ensure_one() # Asegura que se ejecuta en un solo registro (la compañía actual)

        # Probar la conexion con la base de datos propio o tercero
        if self.cross_ruc_query_base_api == 'own':
            # Asumiendo que 'verify_connection_res_partner_search_config' es un método válido en self.env.company
            res = self.env.company.verify_connection_res_partner_search_config()

            if isinstance(res, bool) and res:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': '¡Conexión exitosa con la interfaz de Crossnexion!',
                        'type': 'rainbow_man',
                    }
                }
            elif isinstance(res, str):
                raise UserError(f'{res}')
            else:
                raise UserError(_('Error desconocido al verificar la conexión con la base de datos propia.'))
        else: # Asumimos 'external'
            try:
                # Usamos un RUC de ejemplo para la prueba de conexión
                test_ruc = '80120640-5'
                res = get_contribuyente_by_ruc(test_ruc) # Llama a la nueva función
                if res: # Si res no es None (encontró datos o un diccionario vacío válido)
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': _('¡Conexión exitosa con la base de datos de tercero! (RUC %s de prueba exitoso: %s)') % (test_ruc, res.get('razonSocial')),
                            'type': 'rainbow_man',
                        }
                    }
                else:
                    # get_contribuyente_by_ruc devolvió None (RUC no encontrado o error manejado internamente)
                    raise UserError(_('Falla en la conexión con la base de consulta externa: El RUC de prueba no devolvió datos.'))
            except UserError as e:
                # UserError ya maneja el mensaje, simplemente lo relanzamos
                raise e
            except Exception as e:
                _logger.error("Error al probar la conexión con la API externa: %s", e)
                raise UserError(_('Ocurrió un error inesperado al probar la conexión con la base de datos externa. Detalles: %s') % e)
