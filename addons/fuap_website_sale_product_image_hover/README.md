# FUAP Website Sale Product Image Hover

## Descripción

Módulo de Odoo que mejora la experiencia de usuario en la tienda online agregando efectos de hover en las imágenes de productos y selectores de variantes inteligentes.

## Funcionalidades Principales

### 1. Efecto Hover en Imágenes

- Muestra una imagen secundaria al pasar el mouse sobre el producto
- Transición suave entre imágenes
- Compatible con todos los templates de productos (grid, carrusel, lista, etc.)

### 2. Selectores de Variantes Inteligentes

#### Botones de Color

- Si el atributo es de tipo "color", muestra círculos de color en lugar de texto
- Los círculos muestran el color real del producto
- Estilo visual mejorado con bordes y efectos hover

#### Selección Múltiple de Atributos

- **Redirección Inteligente**: Solo redirige al producto cuando se seleccionan TODOS los atributos disponibles
- **Feedback Visual**: Muestra mensajes indicando cuántos atributos faltan por seleccionar
- **Ejemplo**: Si un producto tiene "Talle" y "Color", el usuario debe seleccionar ambos antes de ir al producto

#### Validación de Combinaciones No Disponibles

- **Validación en Tiempo Real**: Verifica si la combinación seleccionada está disponible antes de redirigir
- **Botones Deshabilitados**: Marca visualmente los botones que no están disponibles con ciertas combinaciones
- **Tooltips Informativos**: Muestra mensajes explicando por qué un botón está deshabilitado
- **Ejemplo**: Si el color "Rojo" no está disponible con "Patas de Aluminio", el botón se marca como deshabilitado

### 3. Compatibilidad

- Funciona con todos los templates de productos de Odoo
- Responsive design para móviles y tablets
- Compatible con carruseles dinámicos

## Configuración

### 1. Configurar Imágenes de Hover

1. Ir a **Ventas > Productos > Productos**
2. Seleccionar un producto
3. En la pestaña "Imágenes", marcar la casilla "Hover" en las imágenes secundarias
4. Guardar

### 2. Configurar Atributos de Color

1. Ir a **Ventas > Configuración > Atributos de Producto**
2. Crear o editar un atributo (ej: "Color")
3. En "Tipo de visualización", seleccionar "Color"
4. Para cada valor del atributo, asignar un color HTML (ej: #FF0000 para rojo)
5. Guardar

### 3. Asignar Atributos a Productos

1. En el producto, ir a la pestaña "Variantes"
2. Agregar líneas de atributos
3. Seleccionar los valores correspondientes
4. Asegurarse de que "Crear variante" esté marcado como "Siempre"

### 4. Configurar Combinaciones No Disponibles

1. En el producto, ir a la pestaña "Variantes"
2. Para las variantes que no quieres que estén disponibles:
   - Desmarcar la casilla "Vendible" en la variante específica
   - O eliminar la variante completamente
3. Guardar el producto
4. El sistema automáticamente detectará las combinaciones no disponibles y las marcará en el frontend

## Uso

### En la Tienda Online

1. **Productos con un solo atributo**: Al hacer clic en el botón, se redirige inmediatamente al producto
2. **Productos con múltiples atributos**:
   - Seleccionar el primer atributo (ej: Talle "M")
   - Aparece un mensaje indicando que falta seleccionar más atributos
   - Seleccionar el segundo atributo (ej: Color "Rojo")
   - Se redirige automáticamente al producto con ambas variantes seleccionadas

### Ejemplos de Uso

- **Camiseta con Talle y Color**: Usuario debe seleccionar "M" y "Rojo" antes de ir al producto
- **Zapatos solo con Talle**: Usuario puede ir directamente al producto seleccionando "42"
- **Producto sin variantes**: Funciona normalmente sin selectores

## Archivos Principales

- `models/product.py`: Lógica de negocio para obtener atributos e imágenes
- `views/website_sale.xml`: Templates XML para mostrar selectores
- `static/src/js/website_sale.js`: JavaScript para interacción y redirección
- `static/src/scss/website_sale.scss`: Estilos CSS para botones y efectos
- `controllers/main.py`: Controlador para validaciones de combinaciones

## Personalización

### Modificar Colores

Editar las variables CSS en `static/src/scss/website_sale.scss`:

```scss
:root {
  --primary-color: #000;
  --secondary-color: #fff;
  --accent-color: #f5f5f5;
  // ... más variables
}
```

### Agregar Nuevos Tipos de Atributos

1. Modificar el método `_get_available_attributes()` en `models/product.py`
2. Agregar lógica específica para el nuevo tipo
3. Actualizar los templates XML y JavaScript según sea necesario

## Solución de Problemas

### Error de Controlador

Si aparece el error `TypeError: WebsiteSale.cart_update() missing 1 required positional argument: 'product_id'`, esto indica un conflicto con las rutas del controlador. El módulo usa rutas con prefijo `/fuap/` para evitar conflictos.

### Verificar que el Controlador Funciona

1. Visitar `/fuap/test` en tu sitio web
2. Deberías ver el mensaje "FUAP Controller is working!"
3. Si no funciona, reinicia el servidor Odoo

### Fallback Automático

Si las validaciones de combinaciones no funcionan, el sistema automáticamente:

- Redirige directamente al producto sin validación
- Muestra advertencias en la consola del navegador
- Mantiene la funcionalidad básica de selección de variantes

## Soporte

Para soporte técnico o consultas, contactar al equipo de desarrollo.
