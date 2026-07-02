import logging
import json
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
from dateutil import parser as date_parser

_logger = logging.getLogger(__name__)

class PagoparWebhookController(http.Controller):

    def _validate_webhook_token(self, webhook_data, api_config=None):
        """Valida el token del webhook"""
        try:
            # Obtener hash del pedido y token del webhook
            hash_pedido = webhook_data.get('hash_pedido') or webhook_data.get('data')
            received_token = webhook_data.get('token')

            if not hash_pedido or not received_token:
                _logger.warning('Webhook sin hash_pedido o token')
                return False

            if not api_config:
                # Buscar configuración de API para generar token esperado
                api_config = request.env['pagopar.api'].sudo().search([], limit=1)

            if not api_config:
                _logger.error('No se encontró configuración de API para validar webhook')
                return False

            # Generar token esperado usando el formato correcto
            expected_token = api_config._generate_token_webhook(hash_pedido)
            print('expected_token', expected_token)
            print('received_token', received_token)

            # Comparar tokens de forma segura
            import hmac
            is_valid = hmac.compare_digest(expected_token, received_token)

            if not is_valid:
                _logger.warning(f'Token de webhook inválido. Esperado: {expected_token}, Recibido: {received_token if received_token else "None"}')

            return is_valid

        except Exception as e:
            _logger.error(f'Error validando token de webhook: {str(e)}')
            return False

    @http.route('/payment/pagopar/webhook', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def pagopar_webhook(self, **post):
        _logger.info('=== INICIO WEBHOOK PAGOPAR ===')
        _logger.info(f'Método: {request.httprequest.method}')
        _logger.info(f'Headers: {dict(request.httprequest.headers)}')

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            _logger.info(f'Raw data recibido: {raw_data}')

            if not raw_data:
                _logger.error('No se recibieron datos en el webhook')
                return request.make_response(
                    json.dumps({'error': 'No data received'}),
                    status=400,
                    headers={'Content-Type': 'application/json'}
                )

            try:
                webhook_data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                _logger.error(f'Error parsing JSON: {str(e)}')
                return request.make_response(
                    json.dumps({'error': 'Invalid JSON format'}),
                    status=400,
                    headers={'Content-Type': 'application/json'}
                )

            _logger.info(f'Datos procesados: {webhook_data}')

            if not ('resultado' in webhook_data and webhook_data.get('respuesta')):
                _logger.error('Formato de webhook inválido - estructura incorrecta')
                return request.make_response(
                    json.dumps({'error': 'Invalid webhook structure'}),
                    status=400,
                    headers={'Content-Type': 'application/json'}
                )

            resultado = webhook_data['resultado'][0] if webhook_data['resultado'] else {}

            pagado = resultado.get('pagado')
            hash_pedido = resultado.get('hash_pedido')
            numero_pedido = resultado.get('numero_pedido')
            forma_pago = resultado.get('forma_pago')
            forma_pago_identificador = resultado.get('forma_pago_identificador')
            monto = resultado.get('monto')
            fecha_pago = resultado.get('fecha_pago')
            fecha_maxima_pago = resultado.get('fecha_maxima_pago')
            numero_comprobante_interno = resultado.get('numero_comprobante_interno')
            ultimo_mensaje_error = resultado.get('ultimo_mensaje_error')
            cancelado = resultado.get('cancelado')
            token_recibido = resultado.get('token')

            _logger.info(f'Datos extraídos - Pagado: {pagado}, Hash: {hash_pedido}, Pedido: {numero_pedido}')

            if not hash_pedido:
                _logger.error('Webhook sin hash_pedido - requerido para validación de token')
                return request.make_response(
                    json.dumps({'error': 'Missing hash_pedido'}),
                    status=400,
                    headers={'Content-Type': 'application/json'}
                )

            transaction = request.env['payment.transaction'].sudo().search([
                ('pagopar_hash_pedido', '=', hash_pedido),
                ('provider_code', '=', 'pagopar')
            ], limit=1)
            api_config = transaction.provider_id._pagopar_get_api_config()

            if not self._validate_webhook_token({'hash_pedido': hash_pedido, 'token': token_recibido}, api_config):
                _logger.error(f'Token de webhook inválido para hash_pedido: {hash_pedido}. Rechazando webhook por seguridad.')
                return request.make_response(
                    json.dumps({'error': 'Token validation failed'}),
                    status=401,
                    headers={'Content-Type': 'application/json'}
                )

            if not transaction:
                _logger.error(f'Transacción no encontrada para hash_pedido: {hash_pedido}')
                return request.make_response(
                    json.dumps({'error': 'Transaction not found'}),
                    status=404,
                    headers={'Content-Type': 'application/json'}
                )

            _logger.info(f'Transacción encontrada: {transaction.reference}')

            # Actualizar datos de la transacción con información del webhook
            self._update_transaction_from_resultado(transaction, resultado)

            # Procesar el estado de la transacción según el campo 'pagado'
            self._process_transaction_from_pagado(transaction, pagado, cancelado)

            _logger.info(f'Webhook procesado exitosamente para transacción {transaction.reference}')

            # Retornar el resultado recibido de Pagopar
            response_data = webhook_data['resultado']

            return request.make_response(
                json.dumps(response_data),
                status=200,
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            _logger.error(f'Error procesando webhook Pagopar: {str(e)}', exc_info=True)
            return request.make_response(
                json.dumps({'error': f'Internal server error: {str(e)}'}),
                status=500,
                headers={'Content-Type': 'application/json'}
            )

    def _update_transaction_from_resultado(self, transaction, resultado):
        """Actualiza los datos de la transacción con información del resultado del webhook"""
        update_vals = {}

        if resultado.get('pagado'):
            update_vals['pagopar_pagado'] = resultado['pagado']

        if resultado.get('hash_pedido'):
            update_vals['pagopar_hash_pedido'] = resultado['hash_pedido']

        if resultado.get('numero_pedido'):
            update_vals['reference'] = resultado['numero_pedido']

        if resultado.get('forma_pago'):
            update_vals['pagopar_forma_pago'] = resultado['forma_pago']

        if resultado.get('forma_pago_identificador'):
            update_vals['pagopar_forma_pago_identificador'] = resultado['forma_pago_identificador']

        if resultado.get('monto') is not None:
            try:
                update_vals['amount'] = float(resultado['monto'])
            except (ValueError, TypeError):
                _logger.warning(f"Monto inválido en webhook: {resultado.get('monto')}")

        if resultado.get('fecha_pago'):
            try:
                update_vals['payment_date'] = date_parser.parse(resultado['fecha_pago'])
            except (ValueError, TypeError) as e:
                try:
                    update_vals['payment_date'] = date_parser.parse(str(resultado['fecha_pago']).split('.')[0])
                except Exception:
                    _logger.warning(f"Error parsing fecha_pago '{resultado.get('fecha_pago')}': {e}")

        if resultado.get('fecha_maxima_pago'):
            try:
                update_vals['payment_deadline'] = date_parser.parse(resultado['fecha_maxima_pago'])
            except (ValueError, TypeError) as e:
                try:
                    update_vals['payment_deadline'] = date_parser.parse(str(resultado['fecha_maxima_pago']).split('.')[0])
                except Exception:
                    _logger.warning(f"Error parsing fecha_maxima_pago '{resultado.get('fecha_maxima_pago')}': {e}")

        if resultado.get('numero_comprobante_interno'):
            update_vals['pagopar_numero_comprobante_interno'] = resultado['numero_comprobante_interno']

        if resultado.get('ultimo_mensaje_error'):
            update_vals['pagopar_ultimo_mensaje_error'] = resultado['ultimo_mensaje_error']

        if resultado.get('cancelado'):
            update_vals['pagopar_cancelado'] = resultado['cancelado']

        if resultado.get('token'):
            update_vals['pagopar_token_recibido'] = resultado['token']

        if update_vals:
            transaction.write(update_vals)
            _logger.info(f'Datos actualizados para transacción {transaction.reference} desde resultado webhook: {update_vals}')

    def _process_transaction_from_pagado(self, transaction, pagado, cancelado):
        """Procesa el estado de la transacción según el campo 'pagado' del webhook"""

        if pagado:
            if transaction.state not in ['done']:
                transaction._set_done()
                _logger.info(f'Transacción {transaction.reference} marcada como completada por pagado')

        if cancelado:
            if transaction.state not in ['cancel']:
                transaction._set_canceled()
                _logger.info(f'Transacción {transaction.reference} cancelada por cancelado')

    @http.route('/payment/pagopar/status/<int:transaction_id>', type='http', auth='public', website=True)
    def pagopar_status(self, transaction_id, **kwargs):
        """Muestra el estado de una transacción Pagopar"""

        try:
            transaction = request.env['payment.transaction'].sudo().browse(transaction_id)

            if not transaction.exists() or transaction.provider_code != 'pagopar':
                return request.not_found()

            success = kwargs.get('success')
            pending = kwargs.get('pending')

            context = {
                'transaction': transaction,
                'success': success == '1',
                'pending': pending == '1',
                'error': success == '0',
            }

            return request.render('pagopar_integration.payment_status', context)

        except Exception as e:
            _logger.error(f'Error mostrando estado: {str(e)}')
            return request.not_found()
