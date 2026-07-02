# Odoo Web Checkout Simplifier

## Descripción

Este addon para Odoo 18 simplifica el proceso de checkout en la tienda web, combinando los pasos de dirección y pago en una sola página intuitiva y moderna.

## Características principales

- **Checkout unificado**: Combina información de contacto, dirección de envío y método de pago en una sola página
- **Interfaz moderna**: Diseño responsivo con Bootstrap y animaciones CSS
- **Mensaje condicional**: Muestra automáticamente las instrucciones de transferencia bancaria cuando se selecciona este método de pago
- **Carga de archivos**: Permite a los clientes subir archivos (comprobantes, notas, etc.) que se guardan como comentarios en la orden de venta
- **Validación en tiempo real**: JavaScript que valida formularios y proporciona retroalimentación inmediata
- **Carga dinámica de estados**: Los estados/provincias se cargan automáticamente según el país seleccionado

## Instalación

1. Copie la carpeta `odoo_web_checkout_simplifier` en el directorio de addons de su instalación de Odoo
2. Actualice la lista de aplicaciones en Odoo
3. Busque "Odoo Web Checkout Simplifier" en la lista de aplicaciones
4. Haga clic en "Instalar"

## Uso

### Para clientes

1. Agregue productos al carrito de compras
2. En la página del carrito, haga clic en "Checkout Rápido" (botón verde)
3. Complete toda la información en el formulario unificado:
   - Información de contacto
   - Dirección de envío
   - Método de pago
   - Archivo adjunto (opcional)
4. Haga clic en "Confirmar Pedido"

### Para administradores

- Los archivos subidos por los clientes se guardan automáticamente como adjuntos en la orden de venta
- Los comentarios sobre archivos adjuntos se agregan al campo "Notas" de la orden
- Las órdenes se procesan normalmente a través del flujo estándar de Odoo

## Configuración

### Métodos de pago

El addon funciona con cualquier método de pago configurado en Odoo. Para transferencias bancarias:

1. Vaya a Facturación > Configuración > Métodos de pago
2. Configure el método "Transferencia bancaria"
3. Agregue las instrucciones bancarias en el campo "Mensaje previo"

### Personalización de mensajes

Para personalizar el mensaje de transferencia bancaria, edite el template XML:

```xml
<!-- En views/website_sale_templates.xml -->
<div class="alert alert-info">
    <h6><i class="fa fa-info-circle me-2"></i>Instrucciones para transferencia bancaria</h6>
    <p>Por favor, realiza la transferencia a la siguiente cuenta bancaria:</p>
    <ul>
        <li><strong>Banco:</strong> Su Banco</li>
        <li><strong>Número de cuenta:</strong> Su número de cuenta</li>
        <li><strong>Titular:</strong> Su empresa</li>
        <li><strong>Concepto:</strong> Pedido #<span t-esc="order.name"/></li>
    </ul>
</div>
```

## Archivos del addon

```
odoo_web_checkout_simplifier/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py
├── models/
│   ├── __init__.py
│   └── sale_order.py
├── security/
│   └── ir.model.access.csv
├── static/src/js/
│   └── checkout_simplifier.js
└── views/
    └── website_sale_templates.xml
```

## Funcionalidades técnicas

### Backend (Python)

- **Modelo extendido**: `sale.order` con campos adicionales para archivos adjuntos
- **Controlador personalizado**: Maneja el formulario unificado y la carga de archivos
- **Rutas AJAX**: Para carga dinámica de estados y información de métodos de pago

### Frontend (JavaScript/XML)

- **Widget JavaScript**: Maneja la interactividad del formulario
- **Templates XML**: Vistas personalizadas para el checkout simplificado
- **CSS dinámico**: Estilos y animaciones para mejorar la experiencia de usuario

### Validaciones

- **Campos requeridos**: Nombre, email, dirección, ciudad, país, método de pago
- **Formato de email**: Validación con expresiones regulares
- **Archivos**: Validación de tipo y tamaño (máximo 10MB)
- **Tipos permitidos**: PDF, JPG, PNG, DOC, DOCX, TXT

## Compatibilidad

- **Odoo**: Versión 18.0
- **Dependencias**: `website_sale`
- **Navegadores**: Chrome, Firefox, Safari, Edge (versiones modernas)
- **Dispositivos**: Responsive design para desktop y móvil

## Soporte

Para reportar problemas o solicitar nuevas características, contacte al desarrollador.

## Licencia

LGPL-3

## Changelog

### Versión 1.0
- Lanzamiento inicial
- Checkout unificado
- Carga de archivos
- Mensajes condicionales de transferencia bancaria
- Validaciones JavaScript
- Diseño responsivo

