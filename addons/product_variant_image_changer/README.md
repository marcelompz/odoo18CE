# Product Variant Image and Price Changer

Un módulo de Odoo 18 que permite a los clientes cambiar dinámicamente la imagen principal y el precio de un producto al hacer clic en miniaturas de diferentes variantes.

## Características

- **Gestión de imágenes por variante**: Asocia múltiples imágenes a cada variante de producto
- **Cambio dinámico de imagen**: Los clientes pueden hacer clic en miniaturas para cambiar la imagen principal
- **Actualización automática de precios**: El precio se actualiza automáticamente según la variante seleccionada
- **Interfaz responsiva**: Optimizado para dispositivos móviles y de escritorio
- **Efectos visuales**: Transiciones suaves y efectos hover profesionales
- **Integración completa**: Se integra perfectamente con el módulo website_sale de Odoo

## Instalación

1. Copia el módulo a tu directorio de addons de Odoo
2. Actualiza la lista de aplicaciones
3. Instala el módulo "Product Variant Image and Price Changer"
4. Configura las imágenes de variantes en tus productos

## Configuración

### Backend

1. Ve a **Ventas → Productos → Productos**
2. Abre un producto que tenga variantes
3. Ve a la pestaña **"Imágenes de Variantes"**
4. Agrega imágenes para cada variante:
   - Selecciona la variante de producto
   - Sube la imagen correspondiente
   - Asigna un nombre descriptivo
   - Ajusta la secuencia si es necesario

### Frontend

Una vez configuradas las imágenes, los clientes verán automáticamente:
- Miniaturas de todas las variantes disponibles debajo de la imagen principal
- Al hacer clic en una miniatura:
  - La imagen principal cambia
  - El precio se actualiza
  - Se muestra información de la variante seleccionada

## Estructura del Módulo

```
product_variant_image_changer/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py
├── models/
│   ├── __init__.py
│   └── product_template.py
├── security/
│   └── ir.model.access.csv
├── static/
│   ├── description/
│   │   └── index.html
│   └── src/
│       ├── css/
│       │   └── product_variant_changer.css
│       └── js/
│           └── product_variant_changer.js
└── views/
    ├── product_frontend_views.xml
    └── product_template_views.xml
```

## Modelos

### ProductVariantImage
- `name`: Nombre de la imagen
- `product_tmpl_id`: Referencia al producto template
- `product_variant_id`: Referencia a la variante específica
- `image`: Imagen binaria
- `sequence`: Orden de visualización
- `active`: Estado activo/inactivo

## API Endpoints

### `/shop/product/get_variant_info`
Obtiene información de una variante específica incluyendo precio e imágenes.

**Parámetros:**
- `variant_id`: ID de la variante de producto

**Respuesta:**
```json
{
    "success": true,
    "variant_id": 123,
    "name": "Producto - Variante",
    "price": 99.99,
    "formatted_price": "$ 99.99",
    "main_image_url": "/web/image/product.product/123/image_1920",
    "variant_images": [...]
}
```

### `/shop/product/get_variant_images`
Obtiene todas las imágenes de variantes para un producto.

**Parámetros:**
- `product_tmpl_id`: ID del producto template

## Personalización

### CSS
El archivo `static/src/css/product_variant_changer.css` contiene todos los estilos personalizables:
- Tamaño de miniaturas
- Efectos de hover
- Colores y transiciones
- Diseño responsivo

### JavaScript
El archivo `static/src/js/product_variant_changer.js` maneja toda la lógica del frontend:
- Event listeners para clics
- Llamadas AJAX
- Actualización del DOM
- Gestión del historial del navegador

## Compatibilidad

- **Odoo 18.0+**
- **Módulos requeridos**: `website_sale`, `product`
- **Navegadores**: Chrome, Firefox, Safari, Edge (versiones modernas)

## Desarrollo

### Agregar nuevas funcionalidades

1. **Nuevos campos en el modelo**:
   ```python
   # En models/product_template.py
   class ProductVariantImage(models.Model):
       _inherit = 'product.variant.image'
       
       nuevo_campo = fields.Char('Nuevo Campo')
   ```

2. **Nuevos endpoints**:
   ```python
   # En controllers/main.py
   @http.route('/shop/product/nueva_funcionalidad', type='json', auth="public")
   def nueva_funcionalidad(self, **kw):
       # Lógica aquí
       pass
   ```

3. **Nuevos estilos**:
   ```css
   /* En static/src/css/product_variant_changer.css */
   .nueva-clase {
       /* Estilos aquí */
   }
   ```

## Solución de Problemas

### Las imágenes no se muestran
- Verifica que las imágenes estén correctamente subidas
- Comprueba los permisos de acceso en `security/ir.model.access.csv`
- Revisa la consola del navegador para errores JavaScript

### Los precios no se actualizan
- Verifica que las variantes tengan precios configurados
- Comprueba que el endpoint `/shop/product/get_variant_info` responda correctamente
- Revisa la configuración de monedas

### Problemas de estilo
- Verifica que los archivos CSS se estén cargando correctamente
- Comprueba conflictos con otros módulos CSS
- Revisa la configuración de assets en `__manifest__.py`

## Licencia

LGPL-3

## Soporte

Para soporte técnico o consultas sobre el módulo, contacta al equipo de desarrollo.

## Changelog

### v18.0.1.0.0
- Versión inicial
- Funcionalidad básica de cambio de imagen y precio
- Interfaz responsiva
- Integración con website_sale

