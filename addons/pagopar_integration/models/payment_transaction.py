import logging
from dateutil import parser as date_parser
from werkzeug import urls

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # Campos específicos de Pagopar
    pagopar_transaccion_id = fields.Char('ID de Transacción Pagopar', readonly=True, copy=False)
    pagopar_proceso_id = fields.Char('ID de Proceso Pagopar', readonly=True, copy=False)
    pagopar_respuesta_codigo = fields.Char('Código de Respuesta Pagopar', readonly=True, copy=False)
    pagopar_payment_url = fields.Char('URL de Pago Pagopar', readonly=True, copy=False)
    pagopar_forma_pago = fields.Char('Forma de Pago Utilizada', readonly=True, copy=False)
    pagopar_estado = fields.Char('Estado en Pagopar', readonly=True, copy=False)
    pagopar_hash_pedido = fields.Char('Hash del Pedido Pagopar', readonly=True, copy=False)
    pagopar_webhook_data = fields.Text('Datos del Webhook', readonly=True, copy=False)

    # Campos adicionales del webhook
    pagopar_pagado = fields.Boolean('Pagado en Pagopar', readonly=True, copy=False)
    pagopar_forma_pago_identificador = fields.Char('Identificador Forma de Pago', readonly=True, copy=False)
    payment_date = fields.Datetime('Fecha de Pago', readonly=True, copy=False)
    payment_deadline = fields.Datetime('Fecha Máxima de Pago', readonly=True, copy=False)
    pagopar_numero_comprobante_interno = fields.Char('Número Comprobante Interno', readonly=True, copy=False)
    pagopar_ultimo_mensaje_error = fields.Text('Último Mensaje de Error', readonly=True, copy=False)
    pagopar_cancelado = fields.Boolean('Cancelado en Pagopar', readonly=True, copy=False)
    pagopar_token_recibido = fields.Char('Token Recibido', readonly=True, copy=False)
    pagopar_payment_method = fields.Char('Método de Pago', readonly=True, copy=False)
    pagopar_paid_at = fields.Datetime('Fecha y Hora de Pago', readonly=True, copy=False)

    # Campo legacy
    pagopar_order_id = fields.Char('Legacy Order ID', readonly=True, copy=False)

    def _get_specific_rendering_values(self, processing_values):
        """ Override to render the redirect form with Pagopar-specific values. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'pagopar':
            return res

        try:
            # Obtener configuración de Pagopar usando el método del proveedor
            api_config = self.provider_id._pagopar_get_api_config()

            if not api_config:
                _logger.error('No se encontró configuración de API de Pagopar')
                return self._handle_api_error("Configuración de Pagopar no encontrada")

            # Obtener datos del partner y direcciones
            partner_data = self._get_partner_data()

            # Convert amount to PYG if needed (Pagopar uses PYG)
            amount_pyg = self.amount
            if self.currency_id.name == 'USD':
                # Approximate USD to PYG conversion (1 USD ≈ 7500 PYG as of 2025)
                amount_pyg = self.amount * 7500  # This should be updated with real-time rates
                _logger.info(f'Converting {self.amount} USD to {amount_pyg} PYG for Pagopar')
            elif self.currency_id.name == 'PYG':
                amount_pyg = self.amount
            else:
                # For other currencies, convert to PYG via USD equivalent
                amount_pyg = self.amount * 7500  # Fallback conversion
                _logger.warning(f'Using fallback conversion for {self.currency_id.name} to PYG')

            # Preparar datos de la transacción para Pagopar
            transaction_data = {
                'reference': self.reference,
                'amount': amount_pyg,  # Use converted PYG amount
                'currency': 'PYG',  # Force PYG currency for Pagopar (Paraguay)
                'description': f'Orden {self.reference} - Pago desde Odoo',
                'partner_name': partner_data.get('nombre', ''),
                'partner_lastname': partner_data.get('apellido', ''),
                'partner_email': partner_data.get('email', ''),
                'partner_phone': partner_data.get('telefono', ''),
                'partner_identification': partner_data.get('identificacion', ''),
                'expiration': '',  # Opcional
                'url_llamada': self._get_webhook_url(),
                'url_retorno': self._get_return_url(),
            }

            _logger.info(f'Datos de transacción preparados para Pagopar: {transaction_data}')

            # Crear transacción en Pagopar
            result = api_config.iniciar_transaccion(transaction_data)

            if result['success']:
                # Actualizar la transacción con los datos de Pagopar
                self.write({
                    'pagopar_transaccion_id': result['transaccion_id'],
                    'pagopar_proceso_id': result['proceso_id'],
                    'pagopar_payment_url': result['payment_url'],
                    'pagopar_hash_pedido': result.get('hash_pedido'),
                    'provider_reference': result['transaccion_id'],
                })

                # Agregar valores de renderizado específicos
                res.update({
                    'pagopar_payment_url': result['payment_url'],
                    'pagopar_transaccion_id': result['transaccion_id'],
                    'pagopar_proceso_id': result['proceso_id'],
                    'pagopar_hash_pedido': result.get('hash_pedido'),
                    'pagopar_respuesta_codigo': result.get('respuesta_codigo'),
                    # Provide the redirect form template for Odoo's payment framework
                    'redirect_form_view': 'pagopar_integration.redirect_form_pagopar',
                })

                _logger.info(f'Transacción Pagopar creada exitosamente: {result["transaccion_id"]} (Hash: {result.get("hash_pedido")})')

            else:
                _logger.error(f'Error al crear transacción en Pagopar: {result["error"]}')
                return self._handle_api_error(result['error'])

        except Exception as e:
            _logger.error(f'Error en procesamiento de Pagopar: {str(e)}')
            return self._handle_api_error(str(e))

        return res

    def _handle_api_error(self, error_message, use_test=False):
        """Maneja errores de API y opcionalmente usa modo test"""
        if use_test:
            _logger.warning("Usando transacción de prueba debido a error en API real")
            try:
                # Crear transacción de prueba
                api_config = self.env['pagopar.api'].search([], limit=1)
                if api_config:
                    test_data = {
                        'reference': self.reference,
                        'amount': self.amount,
                        'currency': self.currency_id.name or 'PYG',
                    }

                    result = api_config.create_test_transaction(test_data)

                    if result['success']:
                        self.write({
                            'pagopar_transaccion_id': result['transaccion_id'],
                            'pagopar_proceso_id': result['proceso_id'],
                            'pagopar_payment_url': result['payment_url'],
                            'pagopar_hash_pedido': result.get('hash_pedido'),
                            'provider_reference': result['transaccion_id'],
                        })

                        return {
                            'pagopar_payment_url': result['payment_url'],
                            'pagopar_transaccion_id': result['transaccion_id'],
                            'pagopar_proceso_id': result['proceso_id'],
                            'pagopar_hash_pedido': result.get('hash_pedido'),
                            'redirect_form_view': 'pagopar_integration.redirect_form_pagopar',
                        }
            except Exception as test_error:
                _logger.error(f'Error creando transacción de prueba: {str(test_error)}')

        # Si no se puede usar test mode, devolver error
        raise UserError(_('Error en Pagopar: %s') % error_message)

    def _get_partner_data(self):
        """Obtiene y prepara datos del partner para Pagopar"""
        partner = self.partner_id
        if not partner:
            return {}

        # Separar nombre en nombre y apellido si es posible
        full_name = partner.name or ''
        name_parts = full_name.split(' ', 1)
        nombre = name_parts[0] if name_parts else ''
        apellido = name_parts[1] if len(name_parts) > 1 else ''

        return {
            'nombre': nombre,
            'apellido': apellido,
            'email': partner.email or '',
            'telefono': partner.phone or partner.mobile or '',
            'identificacion': self._get_partner_identification(),
        }

    def _get_webhook_url(self):
        """Genera URL de webhook para callbacks de Pagopar"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/payment/pagopar/webhook"

    def _get_return_url(self):
        """Genera URL de retorno después del pago"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/payment/pagopar/return?reference={self.reference}"

    def _get_processing_info(self):
        """Returns processing info for Pagopar transactions"""
        res = super()._get_processing_info()
        if self.provider_code == 'pagopar':
            if self.pagopar_payment_url:
                res.update({
                    'redirect_form_html': self.env['ir.qweb']._render(
                        'pagopar_integration.redirect_form_pagopar',
                        {'pagopar_payment_url': self.pagopar_payment_url}
                    )
                })
        return res

    def _get_partner_identification(self):
        """
        Obtiene la identificación del partner, procesándola para que sea
        compatible con la API de Pagopar (sin dígito verificador).
        """
        # Establecemos un valor por defecto
        partner_identification = ''
        
        # Verificamos que el partner exista
        if self.partner_id and self.partner_id.vat:
            # Usamos partner.vat directamente, es más claro y eficiente
            vat = self.partner_id.vat

            # Limpiamos el VAT
            trash = '.,;:!?"\''
            for char in trash:
                vat = vat.replace(char, '')
            
            if vat:
                # Limpiamos espacios en blanco por si acaso
                vat = vat.strip()
                
                # Verificamos si contiene un guion (indicativo de RUC)
                if '-' in vat:
                    # Dividimos la cadena por el guion y tomamos la primera parte
                    partner_identification = vat.split('-')[0]
                else:
                    # Si no hay guion, es una CI, la tomamos tal cual
                    partner_identification = vat
                    
        return partner_identification

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Busca la transacción basada en los datos de notificación"""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'pagopar' or len(tx) == 1:
            return tx

        # Buscar por ID de orden de Pagopar
        pagopar_order_id = notification_data.get('order_id')
        if pagopar_order_id:
            tx = self.search([('pagopar_order_id', '=', pagopar_order_id)])

        if not tx:
            # Buscar por referencia del proveedor
            provider_reference = notification_data.get('external_reference')
            if provider_reference:
                tx = self.search([('reference', '=', provider_reference)])

        return tx

    def _process_notification_data(self, notification_data):
        """Procesa los datos de notificación de Pagopar"""
        super()._process_notification_data(notification_data)

        if self.provider_code != 'pagopar':
            return

        try:
            # Obtener configuración de API
            api_config = self.provider_id._pagopar_get_api_config()

            # Procesar la notificación
            success = api_config.process_webhook_notification(notification_data)

            if success:
                # Guardar datos del webhook
                self.pagopar_webhook_data = str(notification_data)

                # Actualizar información adicional si está disponible
                if notification_data.get('payment_method'):
                    self.pagopar_payment_method = notification_data['payment_method']
                if notification_data.get('paid_at'):
                    try:
                        self.pagopar_paid_at = date_parser.parse(notification_data['paid_at'])
                    except (ValueError, TypeError) as e:
                        _logger.warning(f'Error parsing paid_at date: {e}')

                _logger.info(f'Notificación de Pagopar procesada exitosamente para transacción {self.reference}')
            else:
                _logger.error(f'Error al procesar notificación de Pagopar para transacción {self.reference}')

        except Exception as e:
            _logger.error(f'Error en _process_notification_data para Pagopar: {str(e)}')

    def _pagopar_check_payment_status(self):
        """Verifica el estado del pago en Pagopar según Paso #4 de la documentación"""
        self.ensure_one()

        if self.provider_code != 'pagopar':
            _logger.warning(f'Transacción {self.reference} no es de Pagopar')
            return False

        if not self.pagopar_hash_pedido:
            _logger.error(f'Transacción {self.reference} no tiene hash_pedido - no se puede consultar estado en Pagopar')
            return False

        try:
            # Obtener configuración de API
            api_config = self.provider_id._pagopar_get_api_config()

            if not api_config:
                _logger.error(f'No se pudo obtener configuración de API para transacción {self.reference}')
                return False

            # Consultar estado en Pagopar usando hash_pedido según Paso #4
            result = api_config.consultar_transaccion(self.pagopar_hash_pedido)

            if result.get('success'):
                # Actualizar información de la transacción con datos del resultado
                update_vals = {}

                if result.get('forma_pago'):
                    update_vals['pagopar_forma_pago'] = result['forma_pago']

                if result.get('forma_pago_identificador'):
                    update_vals['pagopar_forma_pago_identificador'] = result['forma_pago_identificador']

                if result.get('monto'):
                    update_vals['amount'] = float(result['monto'])

                if result.get('fecha_pago') and result['fecha_pago']:
                    try:
                        from dateutil import parser as date_parser
                        update_vals['payment_date'] = date_parser.parse(result['fecha_pago'])
                    except (ValueError, TypeError) as e:
                        _logger.warning(f'Error parsing fecha_pago: {e}')

                if result.get('numero_pedido'):
                    update_vals['provider_reference'] = result['numero_pedido']

                if update_vals:
                    self.write(update_vals)

                # Actualizar estado de la transacción según el campo 'pagado'
                if result.get('pagado') and self.state != 'done':
                    self._set_done()
                    _logger.info(f'Transacción {self.reference} actualizada a completada desde consulta Pagopar')
                elif result.get('cancelado') and self.state != 'cancel':
                    self._set_canceled()
                    _logger.info(f'Transacción {self.reference} cancelada desde consulta Pagopar')
                elif not result.get('pagado') and not result.get('cancelado') and self.state not in ['done', 'cancel']:
                    # Si no está pagado ni cancelado, mantener como pendiente
                    if self.state == 'draft':
                        self._set_pending()
                    _logger.info(f'Transacción {self.reference} pendiente según consulta Pagopar')

                return True
            else:
                _logger.error(f'Error al consultar estado en Pagopar para transacción {self.reference}: {result.get("error")}')
                return False

        except Exception as e:
            _logger.error(f'Error en _pagopar_check_payment_status: {str(e)}')
            return False

    def action_check_pagopar_status(self):
        """Acción para verificar manualmente el estado en Pagopar"""
        success_count = 0
        error_count = 0

        for tx in self:
            if tx.provider_code == 'pagopar':
                if tx._pagopar_check_payment_status():
                    success_count += 1
                else:
                    error_count += 1

        if error_count > 0 and success_count == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('No se pudo verificar el estado en Pagopar para ninguna transacción'),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        elif error_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Parcialmente Actualizado'),
                    'message': _('Se actualizaron %d transacciones, pero %d tuvieron errores') % (success_count, error_count),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Estado Actualizado'),
                    'message': _('El estado de las transacciones ha sido actualizado desde Pagopar'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def _finalize_post_processing(self):
        super()._finalize_post_processing()

        pagopar_txs = self.filtered(lambda tx: tx.provider_code == 'pagopar')
        if pagopar_txs:
            for tx in pagopar_txs:
                if tx.state == 'done' and not tx.pagopar_paid_at:
                    tx.pagopar_paid_at = fields.Datetime.now()
                    _logger.info(f'Set paid_at timestamp for Pagopar transaction {tx.reference}')
