import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('pagopar', 'Pagopar')],
        ondelete={'pagopar': 'set default'}
    )

    # Campos específicos de Pagopar
    pagopar_token_privado = fields.Char(
        'Token Privado',
        help='Token privado proporcionado por Pagopar para autenticación',
        groups='base.group_system',
        required_if_provider='pagopar'
    )
    pagopar_token_publico = fields.Char(
        'Token Público',
        help='Token público proporcionado por Pagopar',
        groups='base.group_system',
        required_if_provider='pagopar'
    )
    pagopar_comercio_id = fields.Char(
        'ID de Comercio',
        help='ID del comercio en Pagopar (opcional, solo para referencia)'
    )

    pagopar_environment = fields.Selection([
        ('sandbox', 'Sandbox (Pruebas)'),
        ('production', 'Producción')
    ], 'Entorno de Pagopar', default='sandbox')

    pagopar_allow_cash_payment = fields.Boolean(
        string='Permitir Pagos en Efectivo',
        default=False,
        help='Permite pagos en efectivo a través de Pagopar'
    )

    # URLs calculadas para integración
    pagopar_webhook_url = fields.Char('URL de Webhook', compute='_compute_pagopar_urls', store=True)
    pagopar_return_url = fields.Char('URL de Retorno', compute='_compute_pagopar_urls', store=True)

    is_published = fields.Boolean('Is Published', default=False, copy=False)

    # Campo computado para mostrar métodos de pago en la vista
    available_payment_method_ids = fields.Many2many(
        'payment.method',
        compute='_compute_available_payment_methods',
        string='Métodos de Pago Disponibles',
        help='Métodos de pago disponibles para este proveedor'
    )

    payment_method_ids = fields.Many2many(
        'payment.method',
        compute='_compute_payment_method_ids',
        string='Payment Methods',
        help='Payment methods for this provider'
    )

    def _get_redirect_form_view(self, is_validation=False):
        if self.code == 'pagopar':
            return self.env.ref('pagopar_integration.redirect_form_pagopar', raise_if_not_found=False)
        return super()._get_redirect_form_view(is_validation=is_validation)


    @api.depends('company_id', 'pagopar_environment')
    def _compute_pagopar_urls(self):
        """Calcula las URLs necesarias para Pagopar"""
        for provider in self:
            if provider.code == 'pagopar':
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
                provider.pagopar_webhook_url = f"{base_url}/payment/pagopar/webhook"
                provider.pagopar_return_url = f"{base_url}/payment/pagopar/return"
            else:
                provider.pagopar_webhook_url = False
                provider.pagopar_return_url = False

    @api.depends('code')
    def _compute_available_payment_methods(self):
        for provider in self:
            if provider.code == 'pagopar':
                pagopar_method = self.env['payment.method'].search([
                    ('code', '=', 'pagopar'),
                    ('active', '=', True)
                ], limit=1)
                provider.available_payment_method_ids = pagopar_method
            else:
                provider.available_payment_method_ids = False

    @api.depends('code')
    def _compute_payment_method_ids(self):
        for provider in self:
            if provider.code == 'pagopar':
                pagopar_method = self.env['payment.method'].search([
                    ('code', '=', 'pagopar'),
                    ('active', '=', True)
                ], limit=1)
                provider.payment_method_ids = pagopar_method
            else:
                provider.payment_method_ids = False

    def _pagopar_get_api_config(self):
        """Obtiene o crea la configuración de API para Pagopar"""
        #self.ensure_one()
        #if self.code != 'pagopar':
        #    raise ValidationError(_('Este proveedor no es de tipo Pagopar'))

        # Buscar configuración existente
        api_config = self.env['pagopar.api'].search([
            ('comercio_token_privado', '=', self.pagopar_token_privado),
            ('comercio_token_publico', '=', self.pagopar_token_publico),
        ], limit=1)

        if not api_config:
            # Crear nueva configuración
            api_config = self.env['pagopar.api'].create({
                'name': f'API {self.name}',
                'comercio_token_privado': self.pagopar_token_privado,
                'comercio_token_publico': self.pagopar_token_publico,
                'comercio_id': self.pagopar_comercio_id or '',
                'is_sandbox': self.pagopar_environment == 'sandbox',
            })
        else:
            # Actualizar configuración existente
            api_config.write({
                'is_sandbox': self.pagopar_environment == 'sandbox',
                'comercio_id': self.pagopar_comercio_id or '',
            })

        return api_config

    def action_test_pagopar_connection(self):
        """Prueba la conexión con la API de Pagopar"""
        self.ensure_one()

        if self.code != 'pagopar':
            return

        try:
            api_config = self._pagopar_get_api_config()
            if not api_config:
                raise UserError(_('No se pudo obtener configuración de API'))

            # Probar obteniendo formas de pago
            result = api_config.obtener_formas_pago()

            if 'error' in result:
                raise UserError(_('Error en API: %s') % result['error'])

            message = _('Conexión exitosa con Pagopar API')
            notification_type = 'success'

        except Exception as e:
            message = _('Error de conexión: %s') % str(e)
            notification_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test de Conexión Pagopar'),
                'message': message,
                'type': notification_type,
                'sticky': notification_type == 'danger',
            }
        }

    @api.constrains('pagopar_token_privado', 'pagopar_token_publico')
    def _check_pagopar_credentials(self):
        """Valida que las credenciales de Pagopar estén configuradas"""
        for provider in self:
            if provider.code == 'pagopar' and provider.state != 'disabled':
                if not provider.pagopar_token_privado:
                    raise ValidationError(_('El Token Privado de Pagopar es requerido.'))
                if not provider.pagopar_token_publico:
                    raise ValidationError(_('El Token Público de Pagopar es requerido.'))

    def _get_default_payment_method_ids(self):
        """Define los métodos de pago por defecto para Pagopar"""
        if self.code == 'pagopar':
            pagopar_method = self.env['payment.method'].search([('code', '=', 'pagopar')], limit=1)
            if pagopar_method:
                return pagopar_method
            else:
                _logger.warning("Método de pago Pagopar no encontrado, creando uno nuevo")
                pagopar_method = self.env['payment.method'].create({
                    'name': 'Pagopar - Pagos en Paraguay',
                    'code': 'pagopar',
                    'sequence': 10,
                    'active': True,
                })
                return pagopar_method
        try:
            return super()._get_default_payment_method_ids()
        except AttributeError:
            return self.env['payment.method']

    @api.model
    def _get_compatible_payment_methods(self, *args, **kwargs):
        methods = super()._get_compatible_payment_methods(*args, **kwargs)

        provider_id = kwargs.get('provider_id') or (args and args[0])
        if provider_id:
            provider = self.browse(provider_id) if isinstance(provider_id, int) else provider_id
            if hasattr(provider, 'code') and provider.code == 'pagopar':
                pagopar_method = self.env['payment.method'].search([('code', '=', 'pagopar')], limit=1)
                if pagopar_method and pagopar_method not in methods:
                    methods |= pagopar_method

        return methods

    def get_available_payment_method_ids(self):
        if self.code == 'pagopar':
            pagopar_method = self.env['payment.method'].search([('code', '=', 'pagopar')], limit=1)
            return pagopar_method.ids if pagopar_method else []
        return super().get_available_payment_method_ids() if hasattr(super(), 'get_available_payment_method_ids') else []

    def _get_supported_currencies(self):
        """Define las monedas soportadas por Pagopar"""
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'pagopar':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in ['PYG', 'USD']
            )
        return supported_currencies

    def _get_available_payment_methods(self):
        """Obtiene los métodos de pago disponibles desde Pagopar"""
        try:
            api_config = self._pagopar_get_api_config()
            if api_config:
                result = api_config.obtener_formas_pago()
                if not 'error' in result:
                    return result
        except Exception as e:
            _logger.error(f'Error obteniendo métodos de pago: {str(e)}')

        return []

    def obtener_formas_pago(self):
        """Acción para obtener formas de pago desde Pagopar API"""
        self.ensure_one()

        if self.code != 'pagopar':
            return

        try:
            api_config = self._pagopar_get_api_config()
            if not api_config:
                raise UserError(_('No se pudo obtener configuración de API'))

            result = api_config.obtener_formas_pago()

            if 'error' in result:
                message = _('Error obteniendo formas de pago: %s') % result['error']
                notification_type = 'danger'
            else:
                # Procesar y mostrar las formas de pago disponibles
                formas_pago = result.get('formas_pago', [])
                if formas_pago:
                    forma_list = ', '.join([fp.get('nombre', 'N/A') for fp in formas_pago])
                    message = _('Formas de pago disponibles: %s') % forma_list
                else:
                    message = _('No se encontraron formas de pago disponibles')
                notification_type = 'success'

        except Exception as e:
            message = _('Error: %s') % str(e)
            notification_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Formas de Pago Pagopar'),
                'message': message,
                'type': notification_type,
                'sticky': notification_type == 'danger',
            }
        }

    def action_fix_pagopar_payment_method(self):
        """Acción para reparar/crear método de pago Pagopar"""
        self.ensure_one()
        if self.code != 'pagopar':
            raise ValidationError(_('Esta acción solo está disponible para proveedores Pagopar'))

        try:
            # Buscar método de pago existente
            pagopar_method = self.env['payment.method'].search([('code', '=', 'pagopar')], limit=1)

            if not pagopar_method:
                # Crear método de pago
                pagopar_method = self.env['payment.method'].create({
                    'name': 'Pagopar - Pagos en Paraguay',
                    'code': 'pagopar',
                    'sequence': 10,
                    'active': True,
                })
                _logger.info("Método de pago Pagopar creado")
                method_created = True
            else:
                method_created = False

            # Asegurar vinculación provider-method (solo desde el lado del método)
            if self not in pagopar_method.provider_ids:
                pagopar_method.write({
                    'provider_ids': [(4, self.id)]
                })
                provider_linked = True
                _logger.info("Proveedor Pagopar vinculado al método de pago")
            else:
                provider_linked = False

            # Preparar mensaje de resultado
            messages = []
            if method_created:
                messages.append("Método de pago creado")
            if provider_linked:
                messages.append("Proveedor vinculado al método")

            if messages:
                message = "Reparación completada: " + ", ".join(messages)
                msg_type = 'success'
            else:
                message = "El método de pago ya estaba correctamente configurado"
                msg_type = 'info'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Método de Pago Reparado'),
                    'message': _(message),
                    'type': msg_type,
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f'Error al reparar método de pago Pagopar: {str(e)}')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error al reparar método de pago: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_debug_payment_methods(self):
        """Debug method to show payment method information"""
        self.ensure_one()
        if self.code != 'pagopar':
            return

        try:
            info = []

            # Check payment method
            pagopar_method = self.env['payment.method'].search([('code', '=', 'pagopar')], limit=1)
            if pagopar_method:
                info.append(f"Método de pago encontrado: {pagopar_method.name}")
                info.append(f"ID: {pagopar_method.id}, Activo: {pagopar_method.active}")
                info.append(f"Proveedores vinculados: {[p.name for p in pagopar_method.provider_ids]}")
            else:
                info.append("Método de pago Pagopar no encontrado")

            # Check provider linkage
            info.append(f"Proveedor actual: {self.name} (ID: {self.id})")

            # Check default methods
            try:
                default_methods = self._get_default_payment_method_ids()
                info.append(f"Métodos por defecto: {[m.name for m in default_methods]}")
            except Exception as e:
                info.append(f"Error obteniendo métodos por defecto: {str(e)}")

            # Check computed field
            self._compute_available_payment_methods()
            info.append(f"Métodos computados: {[m.name for m in self.available_payment_method_ids]}")

            # Check payment_method_ids field
            self._compute_payment_method_ids()
            info.append(f"payment_method_ids: {[m.name for m in self.payment_method_ids]}")

            # Check available method IDs
            try:
                method_ids = self.get_available_payment_method_ids()
                info.append(f"Available method IDs: {method_ids}")
            except Exception as e:
                info.append(f"Error getting method IDs: {str(e)}")

            # Force linkage check
            self._ensure_pagopar_method_linkage()
            info.append("Forzado enlace automático")

            message = "<br/>".join(info)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Debug Información'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error en Debug'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _pagopar_get_supported_countries(self):
        """Obtiene los países soportados por Pagopar"""
        self.ensure_one()
        if self.code != 'pagopar':
            return self.env['res.country']

        paraguay = self.env['res.country'].search([('code', '=', 'PY')], limit=1)
        return paraguay if paraguay else self.env['res.country']

    def _pagopar_format_amount(self, amount, currency):
        return int(amount)

    def website_publish_button(self):
        self.ensure_one()
        self.is_published = not self.is_published
        return True

    @api.model
    def create(self, vals):
        """Override create to ensure payment method linkage for Pagopar providers"""
        provider = super().create(vals)
        if provider.code == 'pagopar':
            provider._ensure_pagopar_method_linkage()
        return provider

    def write(self, vals):
        """Override write to ensure payment method linkage for Pagopar providers"""
        result = super().write(vals)
        for provider in self:
            if provider.code == 'pagopar':
                provider._ensure_pagopar_method_linkage()
        return result

    def _ensure_pagopar_method_linkage(self):
        """Ensure Pagopar payment method is properly linked to this provider"""
        if self.code != 'pagopar':
            return

        pagopar_method = self.env['payment.method'].search([('code', '=', 'pagopar')], limit=1)
        if pagopar_method and self not in pagopar_method.provider_ids:
            pagopar_method.write({'provider_ids': [(4, self.id)]})
            _logger.info(f"Auto-linked Pagopar method to provider {self.name}")
