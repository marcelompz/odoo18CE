# Pagopar Payment Integration for Odoo 18

## 📋 Descripción

Este módulo proporciona una integración completa con **Pagopar**, la plataforma de pagos líder en Paraguay, permitiendo procesar pagos de forma segura y eficiente directamente desde Odoo 18.

## ✨ Características Principales

### 🔧 Funcionalidades Core
- ✅ **Integración completa con API de Pagopar** según especificaciones técnicas oficiales
- ✅ **Procesamiento de pagos** con múltiples métodos (tarjetas, transferencias, efectivo)
- ✅ **Manejo de webhooks** para notificaciones automáticas de estado de pago
- ✅ **Validación de transacciones** con verificación de firma HMAC-SHA256
- ✅ **Soporte multi-empresa** con configuraciones independientes
- ✅ **Logging completo** de transacciones y eventos

### 💳 Métodos de Pago Soportados
- 💳 Tarjetas de Crédito (Visa, Mastercard)
- 💸 Tarjetas de Débito
- 🏦 Transferencias Bancarias
- 💵 Pagos en Efectivo (opcional)

### 🔒 Seguridad
- 🔐 Validación de firmas digitales en webhooks
- 🌐 Filtrado de IPs permitidas para webhooks
- 🔑 Almacenamiento seguro de credenciales
- 📊 Logging de actividades sospechosas

### 🎨 Interfaz de Usuario
- 📱 Páginas responsive para resultados de pago
- ⚡ JavaScript integrado para verificación de estado
- 🎯 Notificaciones en tiempo real
- 📊 Dashboard de estadísticas

## 🚀 Instalación y Activación

### Requisitos Previos
- Odoo 18.0
- Python 3.8+
- Módulos: `account`, `payment`, `website_sale_payment`
- Conexión HTTPS en producción

### Dependencias Python
```bash
pip install requests
```

### Instalación del Módulo
1. Copiar el módulo a la carpeta `addons` de Odoo
2. Actualizar la lista de módulos en Apps
3. Buscar "Pagopar Payment Integration"
4. Hacer clic en "Instalar"

### 📋 Guía de Activación Rápida

#### 1. Obtener Credenciales de Pagopar
- Registrarse en [pagopar.com](https://pagopar.com)
- Acceder al panel de desarrollador
- Generar API Key y Secret Key para sandbox

#### 2. Configurar en Odoo
```
Facturación → Configuración → Proveedores de Pago → Pagopar
- Estado: Prueba
- Entorno: Sandbox
- API Key: pk_test_xxx
- Secret Key: sk_test_xxx
```

#### 3. Configurar URLs en Pagopar
```
Webhook URL: https://su-dominio.com/payment/pagopar/webhook
Return URL: https://su-dominio.com/payment/pagopar/return
```

#### 4. Probar Conexión
- Hacer clic en "Probar Conexión" en la configuración
- Verificar mensaje de éxito

#### 5. Realizar Transacción de Prueba
- Crear factura de prueba
- Seleccionar Pagopar como método de pago
- Usar tarjeta de prueba: 4111111111111111

📖 **Para instrucciones detalladas, consulte el [MANUAL_DE_USO.md](MANUAL_DE_USO.md)**

## ⚙️ Configuración

### 1. Obtener Credenciales de Pagopar
1. Registrarse en [Pagopar](https://pagopar.com)
2. Obtener API Key y Secret Key del panel de desarrollador
3. Configurar URLs de webhook y retorno

### 2. Configurar en Odoo
1. Ir a **Facturación → Configuración → Proveedores de Pago**
2. Activar y configurar **Pagopar**
3. Ingresar credenciales:
   - **API Key**: `pk_live_xxx` (producción) o `pk_test_xxx` (pruebas)
   - **Secret Key**: `sk_live_xxx` (producción) o `sk_test_xxx` (pruebas)
   - **Entorno**: Sandbox o Producción

### 3. Configuración Avanzada
1. Ir a **Facturación → Pagopar → Configuración Avanzada**
2. Configurar:
   - Timeouts y reintentos
   - Seguridad de webhooks
   - Logging y monitoreo
   - Notificaciones por email

### 4. URLs de Webhook
Configurar en el panel de Pagopar:
- **Webhook URL**: `https://tudominio.com/payment/pagopar/webhook`
- **Return URL**: `https://tudominio.com/payment/pagopar/return`

## 🔄 Flujo de Pago

1. **Cliente inicia pago** en Odoo (e-commerce, factura, etc.)
2. **Odoo crea orden** en Pagopar vía API
3. **Cliente es redirigido** a página de pago de Pagopar
4. **Cliente completa pago** en plataforma Pagopar
5. **Pagopar envía webhook** a Odoo notificando el resultado
6. **Odoo actualiza estado** de la transacción automáticamente
7. **Cliente ve resultado** en página de confirmación

## 📖 Uso

### Para Desarrolladores

#### Crear una Transacción de Pago
```python
# Obtener proveedor Pagopar
provider = self.env['payment.provider'].search([('code', '=', 'pagopar')], limit=1)

# Crear transacción
transaction = self.env['payment.transaction'].create({
    'reference': 'PAY-001',
    'provider_id': provider.id,
    'amount': 150000,  # En guaraníes
    'currency_id': self.env.ref('base.PYG').id,
    'partner_id': partner.id,
})

# Obtener URL de pago
rendering_values = transaction._get_specific_rendering_values({})
payment_url = rendering_values.get('pagopar_payment_url')
```

#### Validar Estado de Pago
```python
# Verificar estado en Pagopar
transaction._pagopar_check_payment_status()
```

### Para Administradores

#### Ver Transacciones
- **Facturación → Pagopar → Transacciones Pagopar**

#### Configurar Métodos de Pago
- **Facturación → Configuración → Proveedores de Pago → Pagopar**

#### Monitorear Actividad
- **Facturación → Pagopar → Configuración Avanzada**

## 🔧 Desarrollo

### Estructura del Módulo
```
pagopar_integration/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── pagopar_api.py          # API principal
│   ├── payment_provider.py     # Extensión proveedor
│   ├── payment_transaction.py  # Extensión transacción
│   └── pagopar_config.py      # Configuración avanzada
├── controllers/
│   ├── __init__.py
│   ├── webhook.py             # Controlador webhooks
│   └── main.py               # Controlador principal
├── views/
│   ├── payment_provider_views.xml
│   ├── payment_transaction_views.xml
│   ├── pagopar_config_views.xml
│   └── payment_templates.xml
├── static/src/
│   ├── js/pagopar_payment_form.js
│   └── css/pagopar_payment.css
├── security/
│   ├── ir.model.access.csv
│   └── pagopar_security.xml
├── data/
│   └── payment_provider_data.xml
├── demo/
│   └── pagopar_demo.xml
└── README.md
```

### Webhooks

#### Endpoint
```
POST /payment/pagopar/webhook
```

#### Headers Requeridos
```
Content-Type: application/json
X-Pagopar-Signature: <hmac_sha256_signature>
```

#### Payload de Ejemplo
```json
{
    "order_id": "12345",
    "status": "paid",
    "amount": 150000,
    "currency": "PYG",
    "payment_method": "credit_card",
    "paid_at": "2024-01-15T10:30:00Z"
}
```

## 🔍 Troubleshooting

### Problemas Comunes

#### ❌ Error de Conexión
- Verificar credenciales API
- Comprobar conectividad a internet
- Revisar configuración de firewall

#### ❌ Webhook No Recibido
- Verificar URL en panel Pagopar
- Comprobar configuración de IP
- Revisar logs de servidor

#### ❌ Firma Inválida
- Verificar Secret Key
- Comprobar configuración de webhook
- Revisar formato de payload

### Logs
```bash
# Ver logs de Pagopar
grep "pagopar" /var/log/odoo/odoo.log

# Logs específicos de webhook
grep "Webhook de Pagopar" /var/log/odoo/odoo.log
```

## 📞 Soporte

### Documentación
- [Documentación Oficial Pagopar](https://soporte.pagopar.com/portal/es/kb/articles/api-integracion-medios-pagos)
- [Documentación Odoo Payments](https://www.odoo.com/documentation/18.0/developer/reference/backend/payments.html)

### Contacto
- **Autor**: Valente Systems - Cristhel Valente
- **Website**: https://valentesystems.com
- **Email**: soporte@valentesystems.com

## 📄 Licencia

Este módulo está licenciado bajo LGPL-3.

## 🚨 Advertencias de Seguridad

⚠️ **IMPORTANTE**:
- Nunca exponer credenciales API en código
- Usar HTTPS en producción
- Validar siempre firmas de webhook
- Mantener logs de transacciones

## 📝 Changelog

### Version 18.0.1.0.0
- ✅ Integración inicial con Pagopar
- ✅ Soporte para todos los métodos de pago
- ✅ Webhooks y validación de firmas
- ✅ Interfaz administrativa completa
- ✅ Páginas de resultado de pago
- ✅ Configuración multi-empresa
- ✅ Sistema de logging avanzado

---

**© 2024 Valente Systems - Cristhel Valente**
