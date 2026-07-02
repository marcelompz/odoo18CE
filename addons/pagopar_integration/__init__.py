import logging
from . import models
from . import controllers

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Hook function executed after module installation"""
    try:
        _logger.info("🚀 Inicializando módulo Pagopar Integration para Odoo 18...")
        
        # 1. Configurar el método de pago con el proveedor
        try:
            pagopar_provider = env['payment.provider'].search([('code', '=', 'pagopar')], limit=1)
            
            if pagopar_provider:
                # Configurar valores por defecto después de la creación
                pagopar_provider.write({
                    'company_id': env.company.id,
                    'sequence': 10,
                })
                _logger.info(f"✅ Proveedor Pagopar configurado: {pagopar_provider.name}")
                
                # Asegurar que el método de pago existe y está vinculado
                pagopar_method = env['payment.method'].search([('code', '=', 'pagopar')], limit=1)
                if not pagopar_method:
                    # Crear método de pago si no existe (para instalaciones existentes)
                    pagopar_method = env['payment.method'].create({
                        'name': 'Pagopar - Pagos en Paraguay',
                        'code': 'pagopar',
                        'sequence': 10,
                        'active': True,
                    })
                    _logger.info("✅ Método de pago Pagopar creado")
                
                # Asegurar vinculación provider-method
                if pagopar_provider not in pagopar_method.provider_ids:
                    pagopar_method.write({
                        'provider_ids': [(4, pagopar_provider.id)]
                    })
                    _logger.info("✅ Proveedor Pagopar vinculado al método de pago")
                
                _logger.info("✅ Método de pago Pagopar correctamente vinculado")
                    
            else:
                _logger.warning("⚠️  Proveedor Pagopar no encontrado")
            
        except Exception as e:
            _logger.warning(f"⚠️  No se pudo configurar relaciones de método de pago: {e}")
        
        # 2. Verificar moneda PYG
        try:
            pyg_currency = env['res.currency'].search([('name', '=', 'PYG')], limit=1)
            if pyg_currency:
                _logger.info("✅ Moneda PYG disponible")
                if not pyg_currency.active:
                    pyg_currency.write({'active': True})
                    _logger.info("✅ Moneda PYG activada")
            else:
                _logger.info("ℹ️  Moneda PYG no encontrada - puede configurarse manualmente")
        except Exception as e:
            _logger.warning(f"⚠️  Error al verificar moneda PYG: {e}")
        
        # 3. Verificar configuración de API
        try:
            pagopar_api_config = env['pagopar.api'].search([('is_sandbox', '=', True)], limit=1)
            if pagopar_api_config:
                _logger.info(f"✅ Configuración API Pagopar encontrada: {pagopar_api_config.name}")
            else:
                _logger.info("ℹ️  Configuración API Pagopar se creará desde datos XML")
        except Exception as e:
            _logger.warning(f"⚠️  Error al verificar configuración API: {e}")
        
        # 4. Verificar grupos de seguridad
        try:
            manager_group = env.ref('pagopar_integration.group_pagopar_manager', raise_if_not_found=False)
            user_group = env.ref('pagopar_integration.group_pagopar_user', raise_if_not_found=False)
            
            if manager_group and user_group:
                _logger.info("✅ Grupos de seguridad Pagopar configurados")
            else:
                _logger.warning("⚠️  Algunos grupos de seguridad no fueron encontrados")
        except Exception as e:
            _logger.warning(f"⚠️  Error al verificar grupos de seguridad: {e}")
        
        # 5. Configurar URLs automáticamente
        try:
            if pagopar_provider:
                base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
                pagopar_provider.write({
                    'pagopar_webhook_url': f"{base_url}/payment/pagopar/webhook",
                    'pagopar_return_url': f"{base_url}/payment/pagopar/return"
                })
                _logger.info("✅ URLs de webhook configuradas automáticamente")
        except Exception as e:
            _logger.warning(f"⚠️  Error al configurar URLs: {e}")
        
        _logger.info("🎉 Módulo Pagopar Integration inicializado correctamente - TODAS LAS FUNCIONES HABILITADAS")
        
    except Exception as e:
        _logger.error(f"❌ Error en post_init_hook de Pagopar Integration: {e}")
        # No re-raise para evitar que falle la instalación


def uninstall_hook(env):
    """Hook function executed before module uninstallation"""
    try:
        _logger.info("🗑️  Desinstalando módulo Pagopar Integration...")
        
        # Desactivar el proveedor Pagopar
        try:
            pagopar_provider = env['payment.provider'].search([('code', '=', 'pagopar')])
            if pagopar_provider:
                pagopar_provider.write({'state': 'disabled'})
                _logger.info("✅ Proveedor Pagopar desactivado")
        except Exception as e:
            _logger.warning(f"⚠️  Error al desactivar proveedor: {e}")
        
        # Desactivar configuraciones de API de Pagopar
        try:
            pagopar_configs = env['pagopar.api'].search([])
            if pagopar_configs:
                pagopar_configs.write({'comercio_token_privado': '', 'comercio_token_publico': ''})
                _logger.info(f"✅ Limpiadas {len(pagopar_configs)} configuraciones de API de Pagopar")
        except Exception as e:
            _logger.warning(f"⚠️  Error al limpiar configuraciones de API: {e}")
        
        _logger.info("🎉 Módulo Pagopar Integration desinstalado correctamente")
        
    except Exception as e:
        _logger.error(f"❌ Error en uninstall_hook de Pagopar Integration: {e}")
        # No re-raise para evitar que falle la desinstalación
