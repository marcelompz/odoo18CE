# 📖 Manual de Uso y Activación - Pagopar Payment Integration

## 🚀 Guía de Activación Paso a Paso

### Paso 1: Preparativos Iniciales

#### 1.1 Verificar Requisitos del Sistema
Antes de instalar el módulo, asegúrese de cumplir con los siguientes requisitos:

```bash
# Verificar versión de Odoo
odoo --version  # Debe ser 18.0 o superior

# Verificar Python
python3 --version  # Debe ser 3.8 o superior

# Instalar dependencias Python
pip install requests hashlib hmac
```

#### 1.2 Crear Cuenta en Pagopar
1. Visite [pagopar.com](https://pagopar.com)
2. Haga clic en "Registrarse" o "Crear Cuenta"
3. Complete el formulario de registro con:
   - Información de la empresa
   - Datos del representante legal
   - Información bancaria
4. Espere la verificación de la cuenta (24-48 horas)
5. Acceda al panel de desarrollador

#### 1.3 Obtener Credenciales API
Una vez aprobada la cuenta:

1. **Acceder al Panel de Desarrollador**
   - Inicie sesión en su cuenta Pagopar
   - Vaya a "Configuración" → "API & Webhooks"

2. **Generar Claves para Sandbox (Pruebas)**
   ```
   API Key Sandbox: pk_test_1234567890abcdef...
   Secret Key Sandbox: sk_test_abcdef1234567890...
   ```

3. **Generar Claves para Producción**
   ```
   API Key Producción: pk_live_1234567890abcdef...
   Secret Key Producción: sk_live_abcdef1234567890...
   ```

⚠️ **IMPORTANTE**: Guarde estas claves en un lugar seguro. Nunca las comparta públicamente.

### Paso 2: Instalación del Módulo

#### 2.1 Instalación Manual
```bash
# 1. Copiar el módulo a la carpeta addons
cp -r pagopar_integration /opt/odoo/addons/

# 2. Cambiar permisos
chown -R odoo:odoo /opt/odoo/addons/pagopar_integration

# 3. Reiniciar Odoo
sudo systemctl restart odoo
```

#### 2.2 Instalación desde Odoo
1. **Acceder a Odoo como Administrador**
2. **Ir a Apps (Aplicaciones)**
3. **Actualizar Lista de Apps**
   - Clic en "Actualizar Lista de Apps"
   - Confirmar la actualización

4. **Buscar el Módulo**
   - Buscar "Pagopar" o "Payment"
   - Localizar "Pagopar Payment Integration"

5. **Instalar el Módulo**
   - Clic en "Instalar"
   - Esperar la instalación completa

#### 2.3 Verificar Instalación
```bash
# Verificar en logs
tail -f /var/log/odoo/odoo.log | grep -i pagopar

# Verificar tablas creadas
psql -U odoo -d <database_name> -c "\dt pagopar*"
```

### Paso 3: Configuración Inicial

#### 3.1 Configurar Proveedor de Pagos

1. **Navegar a Configuración**
   ```
   Menú: Facturación → Configuración → Proveedores de Pago
   ```

2. **Buscar Pagopar**
   - Debería aparecer "Pagopar" en la lista
   - Estado inicial: "Deshabilitado"

3. **Configurar Credenciales**
   ```
   Nombre: Pagopar Paraguay
   Estado: Prueba (para comenzar)
   Entorno: Sandbox
   API Key: pk_test_... (su clave de pruebas)
   Secret Key: sk_test_... (su clave secreta de pruebas)
   URL Base: https://api.pagopar.com
   ```

4. **Configurar Métodos de Pago**
   ```
   ✅ Permitir Tarjetas de Crédito
   ✅ Permitir Tarjetas de Débito
   ✅ Permitir Transferencia Bancaria
   ❌ Permitir Pago en Efectivo (opcional)
   ```

5. **Guardar Configuración**
   - Clic en "Guardar"
   - El sistema generará automáticamente las URLs de webhook

#### 3.2 Configurar URLs en Pagopar

1. **Acceder al Panel de Pagopar**
   - Ir a "Configuración" → "Webhooks"

2. **Configurar Webhook URL**
   ```
   URL: https://su-dominio.com/payment/pagopar/webhook
   Eventos: payment.completed, payment.failed, payment.cancelled
   ```

3. **Configurar Return URL**
   ```
   URL de Retorno: https://su-dominio.com/payment/pagopar/return
   ```

4. **Configurar Allowed Origins**
   ```
   Dominios Permitidos: https://su-dominio.com
   ```

#### 3.3 Probar Conexión

1. **En la configuración del proveedor Pagopar**
2. **Clic en "Probar Conexión"**
3. **Verificar mensaje de éxito**
   - ✅ "Conexión exitosa con Pagopar"
   - ❌ Si hay error, revisar credenciales

### Paso 4: Configuración Avanzada

#### 4.1 Acceder a Configuración Avanzada
```
Menú: Facturación → Pagopar → Configuración Avanzada
```

#### 4.2 Configurar Parámetros API
```
Timeout de API: 30 segundos
Máximo de Reintentos: 3
Retraso entre Reintentos: 5 segundos
```

#### 4.3 Configurar Seguridad
```
✅ Validar Firma del Webhook
❌ Validar IP del Webhook (inicialmente)
✅ Habilitar Logging Detallado (para pruebas)
```

#### 4.4 Configurar Notificaciones
```
❌ Enviar Notificaciones por Email (opcional)
Precisión de Montos: 2 decimales
Horas de Expiración de Orden: 24
✅ Confirmar Pagos Automáticamente
```

### Paso 5: Pruebas en Ambiente Sandbox

#### 5.1 Crear Transacción de Prueba

1. **Desde Facturación**
   ```
   Facturación → Clientes → Facturas → Crear
   ```

2. **Crear Factura de Prueba**
   ```
   Cliente: Seleccionar o crear cliente de prueba
   Productos: Añadir productos con montos de prueba
   Total: Ej. 150.000 PYG
   ```

3. **Registrar Pago**
   ```
   Clic en "Registrar Pago"
   Método de Pago: Pagopar
   ```

#### 5.2 Simular Pago en Sandbox

1. **Usuario será redirigido a página de Pagopar**
2. **Usar datos de prueba de Pagopar:**
   ```
   Tarjeta de Crédito de Prueba:
   Número: 4111111111111111
   Vencimiento: 12/25
   CVV: 123
   
   Tarjeta que Falla (para probar errores):
   Número: 4000000000000002
   ```

3. **Completar Flujo de Pago**
4. **Verificar Redirección de Vuelta a Odoo**

#### 5.3 Verificar Resultados

1. **En la Transacción**
   ```
   Facturación → Pagopar → Transacciones Pagopar
   ```

2. **Verificar Campos Pagopar:**
   ```
   - ID de Orden Pagopar: ✅
   - Método de Pago Usado: ✅
   - Fecha de Pago: ✅
   - Estado: "Completado"
   ```

3. **Verificar Logs**
   ```bash
   tail -f /var/log/odoo/odoo.log | grep "Pagopar"
   ```

### Paso 6: Activación en Producción

#### 6.1 Cambiar a Credenciales de Producción

1. **Acceder a Configuración del Proveedor**
2. **Cambiar Entorno**
   ```
   Entorno: Producción
   API Key: pk_live_... (su clave de producción)
   Secret Key: sk_live_... (su clave secreta de producción)
   ```

3. **Actualizar URLs en Pagopar Producción**
   - Configurar las mismas URLs pero en el panel de producción

#### 6.2 Configurar SSL/HTTPS

⚠️ **CRÍTICO para Producción**:
```bash
# Verificar que su dominio tenga SSL válido
curl -I https://su-dominio.com

# Las URLs de webhook DEBEN usar HTTPS
```

#### 6.3 Activar Proveedor

1. **Cambiar Estado a "Habilitado"**
2. **Realizar Transacción de Prueba Real**
3. **Monitorear por 24 horas**

### Paso 7: Uso Cotidiano

#### 7.1 Procesar Pagos desde E-commerce

1. **Configurar Website**
   ```
   Website → Configuración → Pagos
   Habilitar Pagopar como método de pago
   ```

2. **Cliente realiza compra**
3. **Sistema automáticamente:**
   - Crea orden en Pagopar
   - Redirige al cliente
   - Recibe webhook de confirmación
   - Actualiza estado del pedido

#### 7.2 Procesar Pagos desde Facturas

1. **Crear Factura Normal**
2. **Enviar Factura al Cliente**
3. **Cliente puede pagar online**
4. **Automáticamente se marca como pagada**

#### 7.3 Monitoreo y Reportes

1. **Dashboard de Transacciones**
   ```
   Facturación → Pagopar → Transacciones Pagopar
   ```

2. **Estadísticas**
   ```
   Facturación → Pagopar → Configuración Avanzada
   Ver sección de "Estadísticas"
   ```

3. **Verificación Manual**
   ```
   Seleccionar transacción → "Verificar Estado en Pagopar"
   ```

## 🔧 Solución de Problemas

### Problema 1: Error "API Key Inválida"

**Síntomas:**
- Error al probar conexión
- Transacciones fallan inmediatamente

**Solución:**
```bash
1. Verificar API Key copiada correctamente
2. Verificar que corresponda al entorno (sandbox/producción)
3. Verificar en panel Pagopar que la clave esté activa
4. Regenerar claves si es necesario
```

### Problema 2: Webhook No Recibido

**Síntomas:**
- Pagos quedan pendientes indefinidamente
- No se actualizan automáticamente

**Solución:**
```bash
1. Verificar URL de webhook en Pagopar
2. Verificar que el dominio sea accesible públicamente
3. Verificar logs: grep "webhook" /var/log/odoo/odoo.log
4. Probar webhook manualmente con curl
```

### Problema 3: "Firma Inválida"

**Síntomas:**
- Error 401 en logs de webhook
- Webhooks rechazados

**Solución:**
```bash
1. Verificar Secret Key
2. Verificar configuración de validación de firma
3. Regenerar Secret Key en Pagopar
4. Actualizar en Odoo
```

### Problema 4: Transacciones Duplicadas

**Síntomas:**
- Múltiples transacciones para un pago
- Cliente cargado varias veces

**Solución:**
```bash
1. Verificar configuración de reintentos
2. Implementar verificación adicional en webhook
3. Revisar logs para identificar causas
```

## 📊 Monitoreo y Mantenimiento

### Verificaciones Diarias
```bash
# Verificar transacciones del día
# Verificar webhooks recibidos
# Revisar logs de errores
```

### Verificaciones Semanales
```bash
# Revisar estadísticas de pagos
# Verificar configuración de URLs
# Actualizar credenciales si es necesario
```

### Verificaciones Mensuales
```bash
# Revisar configuración de seguridad
# Actualizar módulo si hay nuevas versiones
# Verificar cumplimiento PCI DSS
```

## 📞 Soporte y Contacto

### Soporte Técnico
- **Email**: soporte@valentesystems.com
- **Teléfono**: +595 21 123-4567
- **Horario**: Lunes a Viernes 8:00-18:00

### Soporte Pagopar
- **Portal**: https://soporte.pagopar.com
- **Email**: developers@pagopar.com

### Documentación Adicional
- [API Pagopar](https://soporte.pagopar.com/portal/es/kb/articles/api-integracion-medios-pagos)
- [Odoo Payment Providers](https://www.odoo.com/documentation/18.0/developer/reference/backend/payments.html)

---

**© 2024 Valente Systems - Cristhel Valente**

*Este manual está actualizado para la versión 18.0.1.0.0 del módulo Pagopar Payment Integration* 