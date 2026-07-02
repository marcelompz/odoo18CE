import logging
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PagoparConfig(models.Model):
    _name = 'pagopar.config'
    _description = 'Configuración Adicional de Pagopar'
    _rec_name = 'name'

    name = fields.Char('Nombre de Configuración', required=True)
    active = fields.Boolean('Activo', default=True)
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)
    
    # Configuraciones de timeout y reintentos
    api_timeout = fields.Integer('Timeout de API (segundos)', default=30, help='Tiempo límite para peticiones a la API')
    max_retries = fields.Integer('Máximo de Reintentos', default=3, help='Número máximo de reintentos para peticiones fallidas')
    retry_delay = fields.Integer('Retraso entre Reintentos (segundos)', default=5)
    
    # Configuraciones de logging
    enable_detailed_logging = fields.Boolean('Habilitar Logging Detallado', default=False)
    log_api_requests = fields.Boolean('Registrar Peticiones API', default=True)
    log_webhook_notifications = fields.Boolean('Registrar Notificaciones Webhook', default=True)
    
    # Configuraciones de notificaciones
    send_email_notifications = fields.Boolean('Enviar Notificaciones por Email', default=False)
    notification_email_template_id = fields.Many2one(
        'mail.template', 
        'Plantilla de Email para Notificaciones',
        domain="[('model', '=', 'payment.transaction')]"
    )
    
    # Configuraciones de seguridad
    validate_webhook_ip = fields.Boolean('Validar IP del Webhook', default=False)
    allowed_webhook_ips = fields.Text('IPs Permitidas para Webhooks', help='Una IP por línea')
    webhook_signature_validation = fields.Boolean('Validar Firma del Webhook', default=True)
    
    # Configuraciones de moneda y formato
    default_currency_id = fields.Many2one('res.currency', 'Moneda por Defecto', default=lambda self: self._get_default_currency())
    amount_precision = fields.Integer('Precisión de Montos', default=2)
    
    # Configuraciones de orden de pago
    order_expiration_hours = fields.Integer('Horas de Expiración de Orden', default=24)
    auto_confirm_payments = fields.Boolean('Confirmar Pagos Automáticamente', default=True)
    
    # Estadísticas y monitoreo
    last_webhook_received = fields.Datetime('Último Webhook Recibido', readonly=True)
    webhook_count_today = fields.Integer('Webhooks Recibidos Hoy', compute='_compute_webhook_stats')
    successful_payments_today = fields.Integer('Pagos Exitosos Hoy', compute='_compute_payment_stats')
    failed_payments_today = fields.Integer('Pagos Fallidos Hoy', compute='_compute_payment_stats')
    
    @api.model
    def _get_default_currency(self):
        """Obtiene la moneda por defecto (Guaraníes Paraguayos)"""
        pyg_currency = self.env['res.currency'].search([('name', '=', 'PYG')], limit=1)
        return pyg_currency.id if pyg_currency else self.env.company.currency_id.id
    
    def _compute_webhook_stats(self):
        """Calcula estadísticas de webhooks"""
        for config in self:
            # Esta sería la implementación completa con un modelo de log de webhooks
            # Por ahora lo dejamos en 0
            config.webhook_count_today = 0
    
    def _compute_payment_stats(self):
        """Calcula estadísticas de pagos"""
        for config in self:
            today = fields.Date.today()
            domain = [
                ('provider_code', '=', 'pagopar'),
                ('company_id', '=', config.company_id.id),
                ('create_date', '>=', today),
                ('create_date', '<', today + timedelta(days=1))
            ]
            
            transactions = self.env['payment.transaction'].search(domain)
            config.successful_payments_today = len(transactions.filtered(lambda t: t.state == 'done'))
            config.failed_payments_today = len(transactions.filtered(lambda t: t.state == 'error'))
    
    @api.constrains('api_timeout')
    def _check_api_timeout(self):
        """Valida que el timeout sea razonable"""
        for config in self:
            if config.api_timeout < 10 or config.api_timeout > 300:
                raise ValidationError(_('El timeout de API debe estar entre 10 y 300 segundos.'))
    
    @api.constrains('max_retries')
    def _check_max_retries(self):
        """Valida el número máximo de reintentos"""
        for config in self:
            if config.max_retries < 0 or config.max_retries > 10:
                raise ValidationError(_('El máximo de reintentos debe estar entre 0 y 10.'))
    
    @api.constrains('allowed_webhook_ips')
    def _check_webhook_ips(self):
        """Valida el formato de las IPs permitidas"""
        for config in self:
            if config.validate_webhook_ip and config.allowed_webhook_ips:
                import ipaddress
                ips = config.allowed_webhook_ips.strip().split('\n')
                for ip in ips:
                    ip = ip.strip()
                    if ip:
                        try:
                            ipaddress.ip_address(ip)
                        except ValueError:
                            raise ValidationError(_('IP inválida: %s') % ip)
    
    @api.model
    def get_active_config(self, company_id=None):
        """Obtiene la configuración activa para una empresa"""
        if not company_id:
            company_id = self.env.company.id
        
        config = self.search([
            ('active', '=', True),
            ('company_id', '=', company_id)
        ], limit=1)
        
        if not config:
            # Crear configuración por defecto si no existe
            config = self.create({
                'name': f'Configuración Pagopar - {self.env.company.name}',
                'company_id': company_id,
            })
        
        return config
    
    def action_test_configuration(self):
        """Prueba la configuración actual"""
        self.ensure_one()
        try:
            # Validar configuraciones básicas
            if self.api_timeout < 10:
                raise ValidationError(_('Timeout muy bajo'))
            
            if self.validate_webhook_ip and not self.allowed_webhook_ips:
                raise ValidationError(_('Debe especificar IPs permitidas si habilita la validación'))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuración Válida'),
                    'message': _('La configuración de Pagopar es válida.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except ValidationError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error de Configuración'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_view_payment_stats(self):
        """Muestra estadísticas detalladas de pagos"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estadísticas de Pagos Pagopar'),
            'res_model': 'payment.transaction',
            'view_mode': 'tree,graph,pivot',
            'domain': [
                ('provider_code', '=', 'pagopar'),
                ('company_id', '=', self.company_id.id)
            ],
            'context': {'search_default_this_month': 1}
        } 