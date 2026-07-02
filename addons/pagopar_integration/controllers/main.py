import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale
import traceback

_logger = logging.getLogger(__name__)

class PagoparMainController(http.Controller):

    @http.route('/payment/pagopar/payment_form', type='http', auth='public', methods=['GET', 'POST'], website=True)
    def pagopar_payment_form(self, **kwargs):
        """Renderiza el formulario de pago de Pagopar"""
        try:
            # Obtener la transacción
            tx_id = kwargs.get('tx_id')
            if not tx_id:
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('ID de transacción no proporcionado')
                })

            transaction = request.env['payment.transaction'].sudo().browse(int(tx_id))

            if not transaction.exists():
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Transacción no encontrada')
                })

            if transaction.provider_code != 'pagopar':
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Esta transacción no es de Pagopar')
                })

            # Si ya tenemos URL de pago, redireccionar
            if transaction.pagopar_payment_url:
                return request.redirect(transaction.pagopar_payment_url)

            # Obtener valores de renderizado
            rendering_values = transaction._get_specific_rendering_values({})

            if rendering_values.get('pagopar_payment_url'):
                return request.redirect(rendering_values['pagopar_payment_url'])
            else:
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('No se pudo generar la URL de pago')
                })

        except Exception as e:
            _logger.error(f'Error en formulario de pago de Pagopar: {str(e)}')
            return request.render('pagopar_integration.payment_error', {
                'error_message': _('Error al procesar el formulario de pago')
            })

    @http.route('/payment/pagopar/test_redirect', type='http', auth='public', methods=['GET'], website=True)
    def test_pagopar_redirect(self, **kwargs):
        """Test route to verify redirect form rendering"""
        try:
            # For testing purposes only - remove in production
            test_url = "https://checkout.pagopar.com/test"
            return request.render('pagopar_integration.redirect_form_pagopar', {
                'pagopar_payment_url': test_url
            })
        except Exception as e:
            _logger.error(f'Error testing redirect form: {str(e)}')
            return request.render('pagopar_integration.payment_error', {
                'error_message': f'Error testing redirect: {str(e)}'
            })

    @http.route('/payment/pagopar/debug_config', type='http', auth='user', methods=['GET'], website=True)
    def debug_pagopar_config(self, **kwargs):
        """Debug route to check Pagopar configuration"""
        try:
            # Get payment provider
            provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'pagopar')
            ], limit=1)

            if not provider:
                return request.make_response("No Pagopar provider configured", headers={'Content-Type': 'text/plain'})

            debug_info = {
                'Provider Found': 'Yes',
                'Provider Name': provider.name,
                'Provider State': provider.state,
                'API Key Configured': 'Yes' if provider.pagopar_api_key else 'No',
                'Secret Key Configured': 'Yes' if provider.pagopar_secret_key else 'No',
                'Base URL': provider.pagopar_base_url,
                'Environment': provider.pagopar_environment,
                'Webhook URL': provider.pagopar_webhook_url,
                'Return URL': provider.pagopar_return_url,
            }

            # Test API configuration
            try:
                api_config = provider._pagopar_get_api_config()
                debug_info['API Config Created'] = 'Yes'

                # Test connection
                connection_test = api_config.test_api_connection()
                debug_info['API Connection Test'] = 'Success' if connection_test['success'] else f"Failed: {connection_test['message']}"

            except Exception as api_error:
                debug_info['API Config Error'] = str(api_error)

            # Format output
            output = "PAGOPAR DEBUG INFORMATION\n" + "="*50 + "\n\n"
            for key, value in debug_info.items():
                output += f"{key}: {value}\n"

            return request.make_response(output, headers={'Content-Type': 'text/plain'})

        except Exception as e:
            error_output = f"DEBUG ERROR: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            return request.make_response(error_output, headers={'Content-Type': 'text/plain'})

    @http.route('/payment/pagopar/validate', type='json', auth='public', methods=['POST'])
    def pagopar_validate_payment(self, **kwargs):
        """Valida el estado de un pago en Pagopar"""
        try:
            order_id = kwargs.get('order_id')
            if not order_id:
                return {'success': False, 'error': 'Order ID requerido'}

            # Buscar la transacción
            transaction = request.env['payment.transaction'].sudo().search([
                ('pagopar_order_id', '=', order_id)
            ], limit=1)

            if not transaction:
                return {'success': False, 'error': 'Transacción no encontrada'}

            # Verificar estado en Pagopar
            success = transaction._pagopar_check_payment_status()

            if success:
                return {
                    'success': True,
                    'status': transaction.state,
                    'reference': transaction.reference
                }
            else:
                return {'success': False, 'error': 'No se pudo verificar el estado'}

        except Exception as e:
            _logger.error(f'Error al validar pago: {str(e)}')
            return {'success': False, 'error': str(e)}

    @http.route('/payment/pagopar/return<string:hash>', type='http', auth='public', methods=['GET'], website=True, csrf=False)
    def pagopar_return(self, hash, **kwargs):
        """Manejo del retorno desde Pagopar después del pago"""
        try:
            hash_pedido = hash

            if not hash_pedido:
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Información de pago incompleta - hash_pedido requerido')
                })

            # Buscar la transacción por hash_pedido
            transaction = request.env['payment.transaction'].sudo().search([
                ('pagopar_hash_pedido', '=', hash_pedido),
                ('provider_code', '=', 'pagopar')
            ], limit=1)

            if not transaction:
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Transacción no encontrada')
                })

            # Verificar estado del pago en Pagopar
            transaction._pagopar_check_payment_status()

            # Redirigir según el estado final
            if transaction.state == 'done':
                return request.render('pagopar_integration.payment_success', {
                    'transaction': transaction
                })
            elif transaction.state == 'pending':
                return request.render('pagopar_integration.payment_pending', {
                    'transaction': transaction
                })
            elif transaction.state == 'cancel':
                return request.render('pagopar_integration.payment_cancelled', {
                    'transaction': transaction
                })
            else:
                return request.render('pagopar_integration.payment_error', {
                    'transaction': transaction,
                    'error_message': _('Estado de pago no reconocido')
                })

        except Exception as e:
            _logger.error(f'Error en retorno de Pagopar: {str(e)}')
            return request.render('pagopar_integration.payment_error', {
                'error_message': _('Error al procesar el retorno del pago')
            })

    @http.route('/payment/pagopar/pay/<model("payment.transaction"):transaction>', type='http', auth='user', website=True)
    def pagopar_pay_transaction(self, transaction=None, **kwargs):
        """Página dedicada para completar un pago pendiente"""
        try:
            # Verificar que el usuario tenga acceso a la transacción
            if not transaction or transaction.partner_id != request.env.user.partner_id:
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Transacción no encontrada o sin acceso')
                })

            if transaction.provider_code != 'pagopar':
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Esta transacción no es de Pagopar')
                })

            if transaction.state == 'done':
                return request.render('pagopar_integration.payment_success', {
                    'transaction': transaction
                })

            # Obtener proveedor Pagopar
            pagopar_provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'pagopar'),
                ('state', '!=', 'disabled')
            ], limit=1)

            if not pagopar_provider:
                return request.render('pagopar_integration.payment_error', {
                    'error_message': _('Pagopar no está disponible')
                })

            return request.render('pagopar_integration.transaction_payment_form', {
                'transaction': transaction,
                'provider': pagopar_provider,
            })

        except Exception as e:
            _logger.error(f'Error al cargar página de pago: {str(e)}')
            return request.render('pagopar_integration.payment_error', {
                'error_message': _('Error al cargar la página de pago')
            })


class PagoparPortalController(CustomerPortal):
    """Extensión del portal del cliente para Pagopar"""

    def _prepare_home_portal_values(self, counters):
        """Agregar conteo de pagos Pagopar al portal"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'pagopar_payment_count' in counters:
            pagopar_payment_count = request.env['payment.transaction'].search_count([
                ('partner_id', '=', partner.id),
                ('provider_code', '=', 'pagopar')
            ])
            values['pagopar_payment_count'] = pagopar_payment_count

        return values

    @http.route(['/my/payments', '/my/payments/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_payments(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """Lista de pagos Pagopar del cliente en el portal"""
        values = self._prepare_portal_layout_values()

        # Filtrar transacciones Pagopar del usuario
        domain = [
            ('partner_id', '=', request.env.user.partner_id.id),
            ('provider_code', '=', 'pagopar')
        ]

        # Aplicar filtros de fecha
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # Filtros disponibles
        filter_options = {
            'all': {'label': _('Todos'), 'domain': []},
            'done': {'label': _('Completados'), 'domain': [('state', '=', 'done')]},
            'pending': {'label': _('Pendientes'), 'domain': [('state', '=', 'pending')]},
            'cancel': {'label': _('Cancelados'), 'domain': [('state', '=', 'cancel')]},
        }

        # Aplicar filtro seleccionado
        if filterby in filter_options:
            domain += filter_options[filterby]['domain']

        # Opciones de ordenamiento
        sort_options = {
            'date': 'create_date desc',
            'amount': 'amount desc',
            'reference': 'reference',
        }

        order = sort_options.get(sortby, 'create_date desc')

        # Buscar transacciones
        transactions = request.env['payment.transaction'].search(domain, order=order)

        values.update({
            'transactions': transactions,
            'page_name': 'payments',
            'default_url': '/my/payments',
            'filter_options': filter_options,
            'filterby': filterby or 'all',
            'sort_options': sort_options,
            'sortby': sortby or 'date',
        })

        return request.render('pagopar_integration.portal_my_payments', values)

    @http.route(['/my/payment/<int:transaction_id>'], type='http', auth='user', website=True)
    def portal_payment_detail(self, transaction_id=None, **kw):
        """Detalle de un pago específico en el portal"""
        transaction = request.env['payment.transaction'].search([
            ('id', '=', transaction_id),
            ('partner_id', '=', request.env.user.partner_id.id),
            ('provider_code', '=', 'pagopar')
        ])

        if not transaction:
            return request.render('pagopar_integration.payment_error', {
                'error_message': _('Pago no encontrado')
            })

        values = self._prepare_portal_layout_values()
        values.update({
            'transaction': transaction,
            'page_name': 'payment_detail',
        })

        return request.render('pagopar_integration.portal_payment_detail', values)
