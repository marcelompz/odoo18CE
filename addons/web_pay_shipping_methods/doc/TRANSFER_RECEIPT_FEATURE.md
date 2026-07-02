# Funcionalidad de Comprobantes de Transferencia

## Descripción

Esta funcionalidad permite a los clientes subir comprobantes de transferencia bancaria durante el proceso de checkout. Los archivos se guardan tanto en el proveedor de pago como en la orden de venta, y se agregan comentarios automáticamente.

## Características

### Para Clientes

- **Subida de archivos**: Los clientes pueden subir comprobantes de transferencia en formatos PDF, JPG, PNG, DOC, DOCX y TXT
- **Validación en tiempo real**: El sistema valida el tipo y tamaño de archivo (máximo 10MB)
- **Interfaz intuitiva**: Campo de subida con botón de búsqueda y visualización del archivo seleccionado
- **Mensajes informativos**: Alertas que explican el proceso y validaciones

### Para Administradores

- **Almacenamiento dual**: Los comprobantes se guardan tanto en el payment provider como en la orden de venta
- **Comentarios automáticos**: Se agregan comentarios automáticamente en el chatter de la orden
- **Vista de gestión**: Los comprobantes se pueden ver y gestionar desde el formulario del payment provider

## Implementación Técnica

### Modelos

#### PaymentProvider (`models/payment_provider.py`)

```python
# Campos agregados
transfer_receipt_attachment = fields.Binary(
    string='Comprobante de Transferencia',
    help='Comprobante de transferencia subido durante el proceso de pago'
)
transfer_receipt_name = fields.Char(
    string='Nombre del Comprobante',
    help='Nombre del archivo del comprobante de transferencia'
)

# Métodos agregados
def _process_transfer_receipt_attachment(self, file_data, filename)
```

### Vistas

#### Payment Provider Form (`views/payment_provider_views.xml`)

- Nueva pestaña "Comprobantes de Transferencia" en el formulario del payment provider
- Campo de subida de archivos con widget binary

#### Payment Page (`views/payment_transfer_receipt_templates.xml`)

- Sección de subida de comprobantes en la página de pago
- Interfaz de usuario mejorada con validaciones

### Controladores

#### WebsiteSaleCustom (`controllers/main.py`)

```python
@http.route(['/shop/confirm_order'], type='http', auth="public", website=True, csrf=False, enctype='multipart/form-data')
def confirm_order(self, **post):
    # Procesa el archivo de comprobante de transferencia
    # Guarda en payment provider y orden de venta
    # Agrega comentarios automáticamente
```

### JavaScript

#### TransferReceipt.js (`static/src/js/TransferReceipt.js`)

- Widget para manejar la subida de archivos
- Validaciones de tipo y tamaño de archivo
- Mensajes de feedback para el usuario
- Formateo de información del archivo

## Flujo de Trabajo

1. **Cliente selecciona método de pago**: En la página de pago, el cliente ve la sección de comprobantes
2. **Subida de archivo**: El cliente puede subir un comprobante de transferencia
3. **Validación**: El sistema valida el tipo y tamaño del archivo
4. **Confirmación**: Al confirmar la orden, el archivo se procesa
5. **Almacenamiento**: El archivo se guarda en:
   - Payment provider (campos `transfer_receipt_attachment` y `transfer_receipt_name`)
   - Orden de venta (como attachment en el chatter)
   - Campo `note` de la orden (como comentario)
6. **Notificación**: Se muestra un mensaje de confirmación al cliente

## Configuración

### Habilitar la funcionalidad

1. Instalar el módulo `web_pay_shipping_methods`
2. La funcionalidad estará disponible automáticamente en la página de pago

### Configurar métodos de pago

1. Ir a Facturación > Configuración > Métodos de pago
2. Seleccionar un payment provider
3. En la pestaña "Comprobantes de Transferencia" se pueden ver los archivos subidos

## Formatos de Archivo Soportados

- **PDF**: Documentos PDF
- **Imágenes**: JPG, JPEG, PNG
- **Documentos**: DOC, DOCX
- **Texto**: TXT

## Límites

- **Tamaño máximo**: 10MB por archivo
- **Tipos permitidos**: Solo los formatos especificados
- **Archivos por orden**: Un comprobante por orden de venta

## Personalización

### Modificar tipos de archivo permitidos

Editar el método `_validateFileType` en `static/src/js/TransferReceipt.js`:

```javascript
_validateFileType: function (file) {
    var allowedTypes = [
        'application/pdf',
        'image/jpeg',
        'image/jpg',
        'image/png',
        // Agregar más tipos aquí
    ];
    return allowedTypes.includes(file.type) ||
           file.name.toLowerCase().match(/\.(pdf|jpg|jpeg|png|doc|docx|txt)$/);
}
```

### Modificar tamaño máximo

Editar el método `_onFileChange` en `static/src/js/TransferReceipt.js`:

```javascript
if (this._validateFileSize(file, 20 * 1024 * 1024)) {
  // 20MB
  // ...
}
```

### Personalizar mensajes

Los mensajes se pueden personalizar editando los métodos `_showSuccessMessage` y `_showErrorMessage` en el archivo JavaScript.

## Troubleshooting

### Problemas comunes

1. **Archivo no se sube**

   - Verificar que el archivo cumple con los requisitos de tipo y tamaño
   - Revisar los logs del servidor para errores

2. **Comprobante no aparece en la orden**

   - Verificar que el controlador está procesando correctamente el archivo
   - Revisar los permisos del usuario

3. **Error de validación**
   - Verificar que el archivo es de un tipo permitido
   - Confirmar que el tamaño no excede el límite

### Logs

Los errores se registran en los logs de Odoo con el prefijo "TransferReceipt":

```
_logger.info(f"Comprobante de transferencia procesado: {file.filename} para orden {order.name}")
_logger.error(f"Error al procesar comprobante de transferencia: {str(e)}")
```

## Seguridad

- Los archivos se validan tanto en el frontend como en el backend
- Se utilizan permisos sudo para operaciones críticas
- Los archivos se almacenan de forma segura en el sistema de attachments de Odoo
- Se registran todas las operaciones en los logs para auditoría
