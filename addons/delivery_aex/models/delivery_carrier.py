# -*- coding: utf-8 -*-
"""
Created on 2025-06-30 17:46:43

@author: drojo
"""
# python
import requests
import hashlib
import uuid
import logging
import base64

# odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# CONSTANTES PARA LA API
AEX_API_URL_PROD = "https://aex.com.py/api/v1/"
AEX_API_URL_TEST = "https://sandbox.aex.com.py/api/v1/"

# CONSTANTES PARA EL SITIO WEB DE SEGUIMIENTO
AEX_WEB_URL_PROD = "https://www.aex.com.py"
AEX_WEB_URL_TEST = "https://sandbox.aex.com.py/web"

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('aex', 'AEX')],
        ondelete={'aex': 'set default'}
    )
    
    aex_clave_publica = fields.Char(string="AEX Clave Pública", groups="base.group_system")
    aex_clave_privada = fields.Char(string="AEX Clave Privada", groups="base.group_system")

    # _#_REFACTOR_#_: Añadimos campos para valores por defecto, configurables desde la UI.
    aex_default_length = fields.Float('Default Length (cm)', default=10)
    aex_default_width = fields.Float('Default Width (cm)', default=10)
    aex_default_height = fields.Float('Default Height (cm)', default=10)
    aex_default_weight = fields.Float('Default Weight (kg)', default=1)
    
    def _aex_get_api_url(self):
        """Devuelve la URL base de la API según el entorno."""
        return AEX_API_URL_PROD if self.prod_environment else AEX_API_URL_TEST

    def _aex_get_web_url(self):
        """Devuelve la URL base del SITIO WEB de AEX según el entorno."""
        return AEX_WEB_URL_PROD if self.prod_environment else AEX_WEB_URL_TEST
        
    def _aex_get_authorization_token(self):
        """Obtiene un token de autorización de AEX."""
        self.ensure_one()
        url = self._aex_get_api_url() + "autorizacion-acceso/generar"
        codigo_sesion = str(uuid.uuid4())
        clave_privada_cifrada = hashlib.md5((self.aex_clave_privada + codigo_sesion).encode('utf-8')).hexdigest()

        payload = {
            'clave_publica': self.aex_clave_publica,
            'clave_privada': clave_privada_cifrada,
            'codigo_sesion': codigo_sesion,
        }
        
        try:
            # AEX usa form-data para este endpoint, no JSON
            response = requests.post(url, data=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get('codigo') == 0:
                return data.get('codigo_autorizacion')
            else:
                raise UserError(_("AEX Authentication Error: %s") % data.get('mensaje'))
        except requests.exceptions.RequestException as e:
            raise UserError(_("AEX Connection Error: %s") % e)

    # _#_REFACTOR_#_: Creamos una función reutilizable para calcular los detalles del paquete.
    # Puede ser usada tanto por rate_shipment (con order) como por send_shipping (con picking).
    def _aex_calculate_package_details(self, lines_container):
        """
        Calcula dimensiones y peso consolidados a partir de líneas de pedido o de albarán.
        :param lines_container: Un recordset de sale.order o stock.picking.
        """
        if lines_container._name == 'sale.order':
            lines = lines_container.order_line
        elif lines_container._name == 'stock.picking':
            lines = lines_container.move_line_ids
        else:
            return {}

        lines_to_ship = lines.filtered(
            lambda l: l.product_id and l.product_id.type in ['consu', 'product']
        )
        if not lines_to_ship:
            return {}

        total_weight_kg = 0.0
        total_length_cm = 0.0
        total_width_cm = 0.0
        total_height_cm = 0.0
        total_item_qty = 0

        for line in lines_to_ship:
            product = line.product_id
            # En sale.order es 'product_uom_qty', en stock.move.line es 'quantity' o 'qty_done'
            qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity

            total_weight_kg += (product.weight or 0.0) * qty
            total_length_cm += (product.aex_product_length or 0.0) * qty
            total_width_cm += (product.aex_product_width or 0.0) * qty
            total_height_cm += (product.aex_product_high or 0.0) * qty
            total_item_qty += qty

        if not total_item_qty:
            return {}
        
        avg_length = total_length_cm / total_item_qty
        avg_width = total_width_cm / total_item_qty
        
        return {
            "peso": total_weight_kg or self.aex_default_weight,
            "largo": avg_length or self.aex_default_length,
            "alto": total_height_cm or self.aex_default_height, # Alto es la suma
            "ancho": avg_width or self.aex_default_width,
        }

    def aex_rate_shipment(self, order):
        """Calcula el costo del envío para una orden de venta."""
        self.ensure_one()
        token = self._aex_get_authorization_token()
        if not token:
            return {'success': False, 'price': 0.0, 'error_message': _("Could not get AEX authorization token."), 'warning_message': False}
        
        origen_partner = self.company_id.partner_id if self.company_id else self.env.company.partner_id
        origen_ciudad_code = self._aex_find_city_code(origen_partner)
        if not origen_ciudad_code:
            return {'success': False, 'price': 0.0, 'error_message': _("Your company's address is missing a valid AEX City."), 'warning_message': False}

        destino_partner = order.partner_shipping_id
        destino_ciudad_code = self._aex_find_city_code(destino_partner)
        if not destino_ciudad_code:
            # Para la cotización, es mejor no ser bloqueante, sino informativo.
            error_msg = _("We could not validate the city '%s' for shipping with AEX. Please check the spelling or contact us.") % (destino_partner.city)
            _logger.warning("AEX Rate: Could not find AEX city for partner %s (City: %s)", destino_partner.name, destino_partner.city)
            return {'success': False, 'price': 0.0, 'error_message': error_msg, 'warning_message': False}

        # _#_REFACTOR_#_: Usamos la nueva función de cálculo.
        package_details = self._aex_calculate_package_details(order)
        if not package_details:
            return {'success': False, 'price': 0.0, 'error_message': _("The order does not contain any items to ship."), 'warning_message': False}

        paquetes = [{
            "peso": package_details['peso'],
            "largo": package_details['largo'],
            "alto": package_details['alto'],
            "ancho": package_details['ancho'],
            "valor": order.amount_untaxed,
            "descripcion": f"Orden de Venta {order.name}",
            "cantidad": 1,
        }]

        payload = {
            "clave_publica": self.aex_clave_publica,
            "codigo_autorizacion": token,
            "origen": origen_ciudad_code,
            "destino": destino_ciudad_code,
            "paquetes": paquetes,
        }
        
        url = self._aex_get_api_url() + 'envios/calcular'
        try:
            _logger.info("AEX Rate Request: %s", payload)
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            _logger.info("AEX Rate Response: %s", data)

            if data.get('codigo') == 0 and data.get('datos'):
                first_service = data['datos'][0]
                total_cost = float(first_service.get('costo_flete', 0))
                for adicional in first_service.get('adicionales', []):
                    total_cost += float(adicional.get('costo', 0))
                    
                return {'success': True, 'price': total_cost, 'error_message': False, 'warning_message': False}
            else:
                error_msg = data.get('mensaje', 'Unknown error.')
                return {'success': False, 'price': 0.0, 'error_message': _("AEX Rate Error: %s") % error_msg, 'warning_message': False}

        except requests.exceptions.RequestException as e:
            return {'success': False, 'price': 0.0, 'error_message': _("AEX Connection Error: %s") % e, 'warning_message': False}

    def aex_send_shipping(self, pickings):
        """Confirma el envío y obtiene la etiqueta."""
        res = []
        for picking in pickings:
            token = self._aex_get_authorization_token()
            if not token:
                raise UserError(_("Could not get AEX authorization token."))
            
            origen_partner = picking.picking_type_id.warehouse_id.partner_id
            origen_ciudad_code = self._aex_find_city_code(origen_partner)
            if not origen_ciudad_code:
                raise UserError(_("Your warehouse's address ('%s') is missing a valid AEX City.") % origen_partner.name)

            destino_partner = picking.partner_id
            destino_ciudad_code = self._aex_find_city_code(destino_partner)
            if not destino_ciudad_code:
                raise UserError(_("Could not validate the city '%s' for the customer '%s'. Please check the contact's address and assign the AEX city manually.") % (destino_partner.city, destino_partner.name))
            
            # _#_REFACTOR_#_: Usamos la función de cálculo para el picking. ¡No más valores hardcodeados!
            package_details = self._aex_calculate_package_details(picking)
            if not package_details:
                raise UserError(_("The picking %s does not contain any items to ship.") % picking.name)

            paquetes = [{
                "peso": package_details['peso'],
                "largo": package_details['largo'],
                "alto": package_details['alto'],
                "ancho": package_details['ancho'],
                "valor": picking.sale_id.amount_untaxed if picking.sale_id else 0,
                "cantidad": 1,
            }]
            
            # _#_REFACTOR_#_: Añadimos 'codigo_operacion' al payload.
            solicitud_payload = {
                "clave_publica": self.aex_clave_publica,
                "codigo_autorizacion": token,
                "codigo_operacion": picking.origin or picking.name, # ID del pedido de venta o del albarán
                "origen": origen_ciudad_code,
                "destino": destino_ciudad_code,
                "paquetes": paquetes,
            }
            
            id_solicitud = None
            id_tipo_servicio = None
            costo_flete = 0.0
            
            url_solicitar = self._aex_get_api_url() + 'envios/solicitar_servicio'
            try:
                _logger.info("AEX Request Service Payload: %s", solicitud_payload)
                solicitud_resp = requests.post(url_solicitar, json=solicitud_payload, timeout=15).json()
                _logger.info("AEX Request Service Response: %s", solicitud_resp)
                
                if solicitud_resp.get('codigo') != 0 or not solicitud_resp.get('datos'):
                    raise UserError(_("AEX Request Service Error: %s") % solicitud_resp.get('mensaje', 'No data returned.'))
                
                datos_solicitud = solicitud_resp['datos']
                id_solicitud = datos_solicitud.get('id_solicitud')
                
                if not datos_solicitud.get('condiciones'):
                    raise UserError(_("AEX did not return any shipping services (conditions) for this request."))

                # Seleccionamos la primera condición/servicio devuelto
                first_condition = datos_solicitud['condiciones'][0]
                id_tipo_servicio = first_condition.get('id_tipo_servicio')
                costo_flete = float(first_condition.get('costo_flete', 0))

            except requests.exceptions.RequestException as e:
                raise UserError(_("AEX Connection Error (Request Service): %s") % e)

            remitente = self._aex_format_partner(picking.picking_type_id.warehouse_id.partner_id)
            pickup_address = self._aex_format_address(picking.picking_type_id.warehouse_id.partner_id, origen_ciudad_code)
            destinatario = self._aex_format_partner(picking.partner_id)
            entrega_address = self._aex_format_address(picking.partner_id, destino_ciudad_code)
            
            confirmar_payload = {
                "clave_publica": self.aex_clave_publica,
                "codigo_autorizacion": token,
                "id_solicitud": id_solicitud,
                "id_tipo_servicio": id_tipo_servicio,
                "remitente": remitente,
                "pickup": pickup_address,
                "destinatario": destinatario,
                "entrega": entrega_address,
            }
            
            url_confirmar = self._aex_get_api_url() + 'envios/confirmar_servicio'
            numero_guia = None
            try:
                _logger.info("AEX Confirm Service Payload: %s", confirmar_payload)
                confirmar_resp = requests.post(url_confirmar, json=confirmar_payload, timeout=20).json()
                _logger.info("AEX Confirm Service Response: %s", confirmar_resp)

                if confirmar_resp.get('codigo') != 0 or not confirmar_resp.get('datos'):
                    raise UserError(_("AEX Confirm Service Error: %s") % confirmar_resp.get('mensaje', 'No data returned.'))
                
                numero_guia = confirmar_resp['datos'].get('numero_guia')
                if not numero_guia:
                    raise UserError(_("AEX did not return a tracking number (numero_guia) after confirmation."))

                # Guardamos el número de guía ANTES de intentar imprimir
                picking.carrier_tracking_ref = numero_guia
                
                # Ahora llamamos a nuestra nueva función de impresión
                self.aex_print_label(picking)

                res.append({
                    'exact_price': costo_flete,
                    'tracking_number': numero_guia
                })

            except requests.exceptions.RequestException as e:
                raise UserError(_("AEX Connection Error (Confirm Service): %s") % e)
        
        return res

    def _aex_format_partner(self, partner):
        """
        Formatea un res.partner al formato de destinatario/remitente de AEX.
        VERSIÓN CORREGIDA SEGÚN SOPORTE DE AEX.
        """
        self.ensure_one()
        doc_type_str = 'CIP' 
        doc_num_str = '0'

        if partner.vat:
            doc_num_str = partner.vat
            if partner.is_company:
                doc_type_str = 'RUC'
            elif partner.l10n_latam_identification_type_id:
                # Si el tipo de doc de Odoo es RUC, lo usamos, si no, CIP.
                doc_type_str = 'RUC' if 'RUC' in partner.l10n_latam_identification_type_id.name.upper() else 'CIP'
        
        if not doc_num_str.isdigit():
            doc_num_str = '0'

        phone_number = partner.phone or partner.mobile or '0999999999'

        return {
            "tipo_documento": doc_type_str,
            "numero_documento": doc_num_str,
            "nombre": partner.name,
            "email": partner.email or "",
            "personeria": "J" if partner.is_company else "F",
            "telefonos": [{"numero": phone_number}]
        }

    def _aex_format_address(self, partner, city_code):
        """
        Formatea la dirección de un res.partner al formato de AEX.
        VERSIÓN FINAL, BASADA EN PRUEBA EXITOSA DE POSTMAN.
        """
        street = partner.street or "Calle Desconocida"
        street2 = partner.street2 or ""
        
        numero_casa_int = 0
        referencias = partner.comment or ""
        
        if street2:
            try:
                numero_str = ''.join(filter(str.isdigit, street2))
                if numero_str:
                    numero_casa_int = int(numero_str)
                else:
                    referencias = f"{street2} {referencias}".strip()
            except (ValueError, TypeError):
                referencias = f"{street2} {referencias}".strip()

        # Payload que replica exactamente la estructura exitosa de Postman.
        address_payload = {
            "codigo": f"ODOO-PARTNER-{partner.id}", # Opcional, pero bueno tenerlo.
            "calle_principal": street,
            "numero_casa": numero_casa_int,
            "codigo_ciudad": city_code,
            "telefono": partner.phone or "0",
            "telefono_movil": partner.mobile or "0",
            "referencias": referencias,
        }
        return address_payload

    def aex_cancel_shipment(self, pickings):
        """Cancela un envío."""
        for picking in pickings:
            tracking_number = picking.carrier_tracking_ref
            if not tracking_number:
                continue
            
            token = self._aex_get_authorization_token()
            payload = {
                "clave_publica": self.aex_clave_publica,
                "codigo_autorizacion": token,
                "numero_guia": tracking_number,
            }
            url = self._aex_get_api_url() + 'envios/cancelar'
            
            try:
                response = requests.post(url, json=payload, timeout=15).json()
                if response.get('codigo') == 0:
                    picking.message_post(body=_("Shipment %s cancelled with AEX.") % tracking_number)
                else:
                    raise UserError(_("AEX Cancel Error: %s") % response.get('mensaje'))
            except requests.exceptions.RequestException as e:
                raise UserError(_("AEX Connection Error (Cancel): %s") % e)

    def aex_get_tracking_link(self, picking):
        """Genera un enlace de seguimiento dinámico según el entorno."""
        if picking.carrier_tracking_ref:
            base_url = self._aex_get_web_url()
            return f"{base_url}/tracking.php?guia={picking.carrier_tracking_ref}"
        return ""

    def _aex_find_city_code(self, partner):
        """
        Intenta encontrar el código de ciudad de AEX para un partner.
        """
        if hasattr(partner, 'aex_city_id') and partner.aex_city_id:
            return partner.aex_city_id.code

        if not partner.city:
            return None

        city_name = partner.city.strip()
        AexCity = self.env['aex.city']
        
        matched_city = AexCity.search([('name', 'ilike', city_name)], limit=1)

        if matched_city and hasattr(partner, 'aex_city_id'):
            try:
                partner.sudo().write({'aex_city_id': matched_city.id})
            except Exception as e:
                _logger.warning("Could not write aex_city_id to partner %s: %s", partner.id, e)
            return matched_city.code
        
        return None

    def aex_print_label(self, picking):
        """
        Obtiene e imprime una etiqueta de AEX para un albarán que ya tiene un número de guía.
        """
        self.ensure_one()
        if not picking.carrier_tracking_ref:
            raise UserError(_("Este albarán no tiene un número de guía de AEX para imprimir."))

        _logger.info("Re-imprimiendo etiqueta AEX para la guía: %s", picking.carrier_tracking_ref)
        
        try:
            token = self._aex_get_authorization_token()
            if not token:
                raise UserError(_("No se pudo obtener el token de autorización de AEX."))

            imprimir_payload = {
                "clave_publica": self.aex_clave_publica,
                "codigo_autorizacion": token,
                "guia": picking.carrier_tracking_ref,
                "formato": "guia" # o "etiqueta"
            }
            url_imprimir = self._aex_get_api_url() + 'envios/imprimir'
            
            imprimir_resp = requests.post(url_imprimir, json=imprimir_payload, timeout=20)
            imprimir_resp.raise_for_status()
            
            content_type = imprimir_resp.headers.get('Content-Type', '')
            if 'application/pdf' in content_type:
                # La forma correcta y directa: pasar los bytes crudos a Odoo.
                label_data = imprimir_resp.content
                file_name = f'AEX-Guia-{picking.carrier_tracking_ref}.pdf'
                log_message = _("Etiqueta AEX re-impresa. Número de Guía: %s") % picking.carrier_tracking_ref
                
                # Adjuntamos el archivo al albarán.
                picking.message_post(body=log_message, attachments=[(file_name, label_data)])
                
                # Opcional: También adjuntar a la orden de venta
                if picking.sale_id:
                    picking.sale_id.message_post(body=log_message, attachments=[(file_name, label_data)])

                _logger.info("Etiqueta AEX %s re-impresa y adjuntada.", picking.carrier_tracking_ref)
                return True # Devolvemos True para indicar éxito.

            elif 'application/json' in content_type:
                error_data = imprimir_resp.json()
                error_message = error_data.get('mensaje', 'Error desconocido durante la impresión de la etiqueta.')
                raise UserError(_("Error al Imprimir Etiqueta AEX: %s") % error_message)
            else:
                raise UserError(_("Error al Imprimir Etiqueta AEX: Formato de respuesta inesperado. Content-Type: %s.") % content_type)

        except requests.exceptions.RequestException as e:
            raise UserError(_("Error de Conexión con AEX (Imprimir Etiqueta): %s") % e)
