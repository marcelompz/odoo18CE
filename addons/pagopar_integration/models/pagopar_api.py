import requests
import json
import logging
import hashlib
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PagoparAPI(models.Model):
    _name = 'pagopar.api'
    _description = 'API de Pagopar'

    name = fields.Char('Nombre', required=True, default='Pagopar API')
    comercio_id = fields.Char('ID de Comercio', help='Solo para referencia - no requerido por la nueva API')
    comercio_token_privado = fields.Char('Token Privado del Comercio', required=True)
    comercio_token_publico = fields.Char('Token Público del Comercio', required=True)
    is_sandbox = fields.Boolean('Modo Sandbox', default=True)
    base_url = fields.Char('URL Base API', compute='_compute_base_url', store=True)

    @api.depends('is_sandbox')
    def _compute_base_url(self):
        for record in self:
            record.base_url = 'https://api.pagopar.com'

    def _generate_token(self, comercio_token_privado, pedido_comercio_id, monto_total):
        """Genera el token SHA1 requerido por Pagopar

        Formato: sha1(comercio_token_privado + idPedido + strval(floatval(monto_total)))
        """

        monto_str = str(int(float(monto_total)))

        token_string = f"{comercio_token_privado}{pedido_comercio_id}{monto_str}"

        _logger.info(f"Generando token con: token_privado({comercio_token_privado[:10]}...) + pedido_id({pedido_comercio_id}) + monto({monto_str})")
        _logger.info(f"Token generado: {hashlib.sha1(token_string.encode('utf-8')).hexdigest()}")

        return hashlib.sha1(token_string.encode('utf-8')).hexdigest()

    def _generate_token_forma_pago(self):
        """Genera token para endpoint de formas de pago: sha1(Private_key + "FORMA-PAGO")"""
        token_string = f"{self.comercio_token_privado}FORMA-PAGO"
        return hashlib.sha1(token_string.encode('utf-8')).hexdigest()

    def _generate_token_consulta(self):
        """Genera token para endpoint de consulta: sha1(Private_key + "CONSULTA")"""
        token_string = f"{self.comercio_token_privado}CONSULTA"
        return hashlib.sha1(token_string.encode('utf-8')).hexdigest()

    def _generate_token_webhook(self, hash_pedido):
        """Genera token para validación de webhook: sha1(private_key + hash_pedido)"""
        token_string = f"{self.comercio_token_privado}{hash_pedido}"
        print('token_string', token_string)
        print('Token privado:', self.comercio_token_privado)
        print('Hash pedido:', hash_pedido)
        return hashlib.sha1(token_string.encode('utf-8')).hexdigest()

    def _make_request(self, endpoint, data):
        """Realiza una petición a la API de Pagopar"""
        url = self.base_url + endpoint

        _logger.info(f"Pagopar API Request: POST {url}")
        _logger.info(f"Request Data: {data}")

        try:
            import requests
            import json

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            _logger.info(f"Response Status: {response.status_code}")
            _logger.info(f"Response Content: {response.text}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    return response_data
                except json.JSONDecodeError:
                    return {'raw_response': response.text}
            else:
                return {'error': f'HTTP {response.status_code}: {response.text}'}

        except Exception as e:
            _logger.error(f"Error en petición Pagopar: {str(e)}")
            return {'error': str(e)}

    def iniciar_transaccion(self, transaction_data):
        """Inicia una transacción con Pagopar"""
        self.ensure_one()

        # Generar token
        pedido_id = transaction_data.get('reference', '')
        monto_total = int(float(transaction_data.get('amount', 0)))  # Convert to integer
        token = self._generate_token(self.comercio_token_privado, pedido_id, monto_total)

        _logger.info(f"Generando token con: token_privado + pedido_id({pedido_id}) + monto({monto_total})")

        # Agregar fecha_maxima_pago - 1 semana desde ahora
        from datetime import datetime, timedelta
        expiration_date = datetime.now() + timedelta(weeks=1)
        fecha_maxima_pago = expiration_date.strftime('%Y-%m-%d %H:%M:%S')

        data = {
            "token": token,
            "public_key": self.comercio_token_publico,
            "monto_total": monto_total,  # Integer, not string
            "tipo_pedido": "VENTA-COMERCIO",
            "id_pedido_comercio": pedido_id,

            "comprador": {
                "nombre": transaction_data.get('partner_name', ''),
                "email": transaction_data.get('partner_email', ''),
                "telefono": transaction_data.get('partner_phone', ''),
                "documento": transaction_data.get('partner_identification', ''),
                "tipo_documento": "CI",
                "ciudad": None,
                "direccion": "",
                "direccion_referencia": None,
                "coordenadas": "",
                "ruc": "",
                "razon_social": transaction_data.get('partner_name', ''),
            },

            "compras_items": [
                {
                    "nombre": transaction_data.get('description', f'Orden {pedido_id} - Pago desde Odoo'),
                    "cantidad": 1,
                    "categoria": "909",
                    "public_key": self.comercio_token_publico,
                    "url_imagen": "",
                    "descripcion": transaction_data.get('description', f'Orden {pedido_id} - Pago desde Odoo'),
                    "id_producto": 1,
                    "precio_total": monto_total,
                    "vendedor_telefono": "",
                    "vendedor_direccion": "",
                    "vendedor_direccion_referencia": "",
                    "vendedor_direccion_coordenadas": "",
                    "ciudad": "1",
                }
            ],
            "fecha_maxima_pago": fecha_maxima_pago,
            "descripcion_resumen": transaction_data.get('description', ''),
            "forma_pago": 9,
        }

        _logger.info(f"Iniciando transacción Pagopar con datos: {data}")

        # Realizar petición a Pagopar
        endpoint = '/api/comercios/2.0/iniciar-transaccion'
        _logger.info(f"Using endpoint: {endpoint}")
        _logger.info(f"Base URL: {self.base_url}")

        response = self._make_request(endpoint, data)

        if 'error' in response:
            return response

        if response.get('respuesta') == True:
            resultado = response.get('resultado', [])
            if resultado and len(resultado) > 0:
                result_data = resultado[0]
                data_hash = result_data.get('data', '')
                pedido = result_data.get('pedido', '')

                _logger.info(f"Transacción Pagopar iniciada exitosamente: Hash={data_hash}, Pedido={pedido}")

                # Construir URL de pago
                if data_hash:
                    payment_url = f"https://www.pagopar.com/pagos/{data_hash}"
                    return {
                        'success': True,
                        'transaccion_id': pedido,
                        'respuesta_codigo': '00',
                        'proceso_id': data_hash,
                        'payment_url': payment_url,
                        'hash_pedido': data_hash,
                    }
                else:
                    _logger.error("No se recibió hash de pedido en la respuesta")
                    return self._handle_api_error("Respuesta incompleta de Pagopar", transaction_data, False)
            else:
                _logger.error("Respuesta exitosa pero sin datos de resultado")
                return self._handle_api_error("Respuesta exitosa sin resultado", transaction_data, False)
        else:
            error_msg = response.get('resultado', 'Error desconocido')
            _logger.error(f"Error en respuesta Pagopar: {error_msg}")
            return self._handle_api_error(error_msg, transaction_data, False)

    def _handle_api_error(self, error_message, transaction_data=None, use_test=True):
        """Maneja errores de API y opcionalmente usa modo test"""
        _logger.error(f"Error al crear transacción en Pagopar: {error_message}")

        if use_test and transaction_data:
            _logger.warning("Usando transacción de prueba debido a error en API real")
            return self.create_test_transaction(transaction_data)
        else:
            return {
                'success': False,
                'error': f'Error de Pagopar: {error_message}',
                'transaccion_id': None,
                'proceso_id': None,
                'respuesta_codigo': None
            }

    def consultar_transaccion(self, hash_pedido):
        """Consulta el estado de una transacción"""
        try:
            token = self._generate_token_consulta()

            data = {
                'hash_pedido': hash_pedido,
                'token': token,
                'token_publico': self.comercio_token_publico
            }

            _logger.info(f'Consultando transacción con hash_pedido: {hash_pedido}')
            response = self._make_request('/api/pedidos/1.1/traer', data)

            if response.get('respuesta') == True and response.get('resultado'):
                resultado = response['resultado'][0] if response['resultado'] else {}

                return {
                    'success': True,
                    'pagado': resultado.get('pagado'),
                    'forma_pago': resultado.get('forma_pago'),
                    'fecha_pago': resultado.get('fecha_pago'),
                    'monto': resultado.get('monto'),
                    'fecha_maxima_pago': resultado.get('fecha_maxima_pago'),
                    'hash_pedido': resultado.get('hash_pedido'),
                    'numero_pedido': resultado.get('numero_pedido'),
                    'cancelado': resultado.get('cancelado'),
                    'forma_pago_identificador': resultado.get('forma_pago_identificador'),
                    'token': resultado.get('token'),
                    'mensaje_resultado_pago': resultado.get('mensaje_resultado_pago'),
                    'raw_response': response
                }
            else:
                error_msg = response.get('resultado', 'Error consultando transacción')
                _logger.error(f"Error en consulta de transacción: {error_msg}")
                return {'success': False, 'error': error_msg}

        except Exception as e:
            _logger.error(f"Error consultando transacción {hash_pedido}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def obtener_formas_pago(self):
        """Obtiene las formas de pago disponibles para el comercio"""
        try:
            token = self._generate_token_forma_pago()

            data = {
                'token': token,
                'token_publico': self.comercio_token_publico
            }

            response = self._make_request('/api/forma-pago/1.1/traer/', data)
            return response

        except Exception as e:
            _logger.error(f"Error obteniendo formas de pago: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_test_transaction(self, transaction_data):
        """Crea una transacción de prueba para desarrollo/testing"""
        _logger.warning("Usando transacción de prueba - NO ES REAL")

        test_transaccion_id = f"TEST_{transaction_data.get('reference', 'UNKNOWN')}"
        test_proceso_id = f"PROC_{test_transaccion_id}"
        test_hash_pedido = f"HASH_{test_transaccion_id}"
        test_payment_url = f"https://www.pagopar.com/pagos/{test_hash_pedido}"

        return {
            'success': True,
            'transaccion_id': test_transaccion_id,
            'respuesta_codigo': '00',
            'proceso_id': test_proceso_id,
            'hash_pedido': test_hash_pedido,
            'payment_url': test_payment_url,
            'raw_response': f'{test_transaccion_id}|00|{test_proceso_id}'
        }
