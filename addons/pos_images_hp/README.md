# POS Images HP - Imágenes de Alta Calidad para Punto de Venta

## 📋 Descripción

Este módulo mejora la calidad visual de las imágenes de productos en el Punto de Venta (POS) de Odoo 18, utilizando imágenes de alta resolución (`image_1920`) en lugar de las miniaturas estándar (`image_128`).

## 🎯 Características Principales

- **Imágenes de Alta Resolución**: Utiliza `image_1920` como imagen principal en el POS
- **Fallback Inteligente**: Si `image_1920` no está disponible, usa `image_1024` como respaldo
- **Configuración Flexible**: Permite activar/desactivar la función desde la configuración del POS
- **Compatibilidad Offline**: Mantiene la funcionalidad en modo offline del POS
- **Optimización de Rendimiento**: Carga eficiente de imágenes sin afectar el rendimiento
- **Responsive Design**: Adaptado para diferentes tamaños de pantalla

## 🚀 Instalación

1. Copia el módulo `pos_images_hp` en tu directorio de addons de Odoo
2. Actualiza la lista de aplicaciones en Odoo
3. Instala el módulo desde la interfaz de aplicaciones
4. Ve a **Punto de Venta > Configuración > Puntos de Venta** y configura el módulo

## ⚙️ Configuración

### Activar Imágenes de Alta Calidad

1. Ve a **Punto de Venta > Configuración > Puntos de Venta**
2. Selecciona o crea una configuración de POS
3. En la sección **"Configuración de Imágenes"**, activa **"Usar Imágenes de Alta Calidad"**
4. Guarda la configuración

### Requisitos del Sistema

- **Odoo 18.0** (Community o Enterprise)
- **Dependencias**: `point_of_sale`, `product`
- **Imágenes de Producto**: Los productos deben tener `image_1920` o `image_1024` para obtener el máximo beneficio

## 🔧 Funcionamiento Técnico

### Backend (Python)

- **Modelo**: Extiende `pos.config` con el campo `use_high_quality_images`
- **Carga de Datos**: Modifica `_pos_ui_models_to_load()` para incluir `image_1920` y `image_1024`
- **Lógica de Fallback**: Implementa la lógica de selección de imagen en `_get_pos_ui_product_product()`

### Frontend (JavaScript/XML)

- **Patches**: Modifica `ProductItem` y `ProductScreen` para usar imágenes de alta calidad
- **Plantillas**: Extiende las plantillas del POS para mostrar las imágenes correctas
- **CSS**: Incluye estilos optimizados para la visualización de imágenes grandes

## 📁 Estructura del Módulo

```
pos_images_hp/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── pos_config.py
├── static/
│   └── src/
│       ├── js/
│       │   └── pos_images_hp.js
│       └── xml/
│           └── pos_images_hp.xml
├── views/
│   └── pos_config_view.xml
└── README.md
```

## 🎨 Personalización

### CSS Personalizado

El módulo incluye estilos CSS que puedes personalizar:

```css
.pos .product-item .product-image {
  object-fit: contain !important;
  max-width: 100% !important;
  max-height: 100% !important;
}
```

### Indicadores de Calidad

El módulo incluye indicadores visuales opcionales:

- **HD**: Para productos con `image_1920`
- **HQ**: Para productos con `image_1024`

## 🔍 Solución de Problemas

### Las imágenes no se muestran en alta calidad

1. Verifica que el campo `use_high_quality_images` esté activado en la configuración del POS
2. Asegúrate de que los productos tengan `image_1920` o `image_1024`
3. Limpia la caché del navegador
4. Reinicia el servicio de Odoo

### Rendimiento lento

1. Verifica que las imágenes no sean excesivamente grandes (>2MB)
2. Considera optimizar las imágenes antes de subirlas
3. Asegúrate de que el servidor tenga suficiente memoria RAM

### Problemas de compatibilidad

1. Verifica que estés usando Odoo 18.0
2. Asegúrate de que las dependencias estén instaladas correctamente
3. Revisa los logs de Odoo para errores específicos

## 📊 Rendimiento

### Optimizaciones Incluidas

- **Lazy Loading**: Las imágenes se cargan solo cuando son necesarias
- **Caché del Navegador**: Aprovecha el caché del navegador para imágenes ya cargadas
- **Compresión**: Utiliza las imágenes ya comprimidas por Odoo
- **Fallback Rápido**: Cambio rápido entre calidades de imagen

### Recomendaciones

- Usa imágenes optimizadas (máximo 1920x1920 píxeles)
- Evita imágenes excesivamente pesadas (>2MB)
- Considera usar CDN para mejorar la velocidad de carga

## 🤝 Soporte

Para soporte técnico o reportar problemas:

- **Autor**: Ing. Daril Díaz
- **Licencia**: LGPL-3
- **Versión**: 1.0

## 📝 Changelog

### Versión 1.0

- Lanzamiento inicial
- Soporte para `image_1920` y `image_1024`
- Configuración desde la interfaz del POS
- Compatibilidad con modo offline
- Optimizaciones de rendimiento

## 🔄 Actualizaciones Futuras

- Soporte para más formatos de imagen
- Configuración de calidad por categoría de producto
- Métricas de rendimiento integradas
- Soporte para imágenes vectoriales

---

**Nota**: Este módulo está diseñado específicamente para Odoo 18.0. Para versiones anteriores, puede requerir modificaciones adicionales.
