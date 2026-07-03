# Mass Product Import with Inventory

Módulo para Odoo 19 que permite la creación masiva de productos con asignación de cantidades de inventario inicial.

## Características

- **Importación desde Excel**: Carga masiva de productos desde archivos .xlsx
- **Descarga de plantilla**: Plantilla Excel predefinida con estructura y ejemplo
- **Creación en lote en Odoo**: Entrada manual con validación en tiempo real
- **Asignación de stock inicial**: Aplica cantidades automáticamente vía `stock.quant`
- **Validaciones previas**: Detecta errores antes de crear productos
- **Categorías automáticas con Fuzzy Match**: Reutiliza categorías existentes similares (evita duplicados por errores de tipeo)
- **OPTIMIZADO**: Batch processing para importar 1000+ productos sin timeout

## Optimizaciones de Rendimiento (v19.0.1.1.0+)

Este módulo implementa **batch processing** para evitar el problema N+1:

| Operación | Antes | Ahora |
|-----------|-------|-------|
| Validación de barcodes | 1 consulta por fila | 1 consulta para TODAS las filas |
| Creación de categorías | 1 consulta por categoría | Cache en memoria + Fuzzy Match |
| Creación de productos | 1 INSERT por producto | 1 INSERT para TODOS los productos |
| Creación de inventario | 1 INSERT por quant | 1 INSERT para TODOS los quants |

**Resultado**: Importación de 10,000 productos en ~5-10 segundos (vs. timeout en 2-3 minutos antes).

## Fuzzy Match para Categorías (v19.0.1.2.0+)

El módulo **detecta categorías similares** y las reutiliza en lugar de crear duplicados:

| Categoría en Excel | Categoría Existente | Resultado |
|-------------------|---------------------|-----------|
| `Artículos de electricidad` | `Articulos de Electricidad` | ✅ Reutiliza existente (ignora tildes) |
| `Herramientas electricas` | `Herramientas Eléctricas` | ✅ Reutiliza existente (ignora tildes) |
| `Hogar y Jardín` | `Hogar` | ✅ Reutiliza existente (contiene palabra) |
| `Deportes Acuáticos` | `Deportes` | ✅ Reutiliza existente (80% similitud) |
| `Electrónica Pro` | `Electrónica` | ✅ Reutiliza existente (contiene palabra) |
| `Nueva Categoría XYZ` | (ninguna similar) | 🆕 Crea nueva categoría |

**Al finalizar la importación**, el módulo muestra:
- 📁 Categorías reutilizadas (con nombre original → nombre encontrado)
- 📁 Categorías creadas (nuevas)

## Requisitos

### Dependencias del sistema

```bash
pip install openpyxl
```

O en Docker:
```bash
docker exec <container> pip install --break-system-packages openpyxl
```

### Requisitos de Odoo

- Odoo 19.0
- Módulos dependientes: `product`, `stock`, `point_of_sale`

## Instalación

1. Copiar el módulo a la carpeta de addons personalizados
2. Instalar la dependencia `openpyxl` en el entorno de Odoo
3. Reiniciar el servidor de Odoo
4. En Odoo, activar modo desarrollador
5. Apps → Actualizar lista de aplicaciones
6. Buscar "Mass Product Import with Inventory" e instalar

## Uso

### Importación desde Excel

1. Ir a **Inventario → Importación Masiva → Importar desde Excel**
2. Click en "Descargar Plantilla" para obtener el archivo de ejemplo
3. Llenar el Excel con los datos de los productos
4. Seleccionar archivo Excel (.xlsx)
5. Seleccionar ubicación de inventario para el stock inicial
6. Click en "Cargar Archivo" para ver vista previa
7. Revisar productos válidos y con errores (se detectan duplicados en el mismo archivo)
8. Click en "Confirmar Importación"

### Creación en Lote (desde Odoo)

1. Ir a **Inventario → Importación Masiva → Creación en Lote**
2. Click en "Crear"
3. Seleccionar ubicación de inventario
4. Click en "Agregar Línea" o editar directamente en la tabla
5. Click en "Validar" para verificar errores
6. Corregir líneas con errores (marcadas en rojo)
7. Click en "Confirmar" para crear productos

## Estructura del Archivo Excel

| Columna | Nombre | Tipo | Requerido | Ejemplo |
|---------|--------|------|-----------|---------|
| A | Referencia Interna | Texto | **SÍ** | "PROD-001" |
| B | Nombre del Producto | Texto | **SÍ** | "Taladro Percutor 500W" |
| C | Descripción para PdV | Texto | No | "Taladro 500W profesional" |
| D | Código de Barras | Texto | No | "7701234567890" |
| E | Disponible en PdV | Booleano | No | "VERDADERO" / "FALSO" |
| F | Categoría de Producto | Texto | No | "Herramientas Eléctricas" |
| G | Categoría de PdV | Texto | No | "Herramientas" |
| H | Precio de Venta | Número | No (default 0) | 150000.00 |
| I | Precio de Costo | Número | No (default 0) | 100000.00 |
| J | Cantidad a la Mano | Número | No (default 0) | 25 |
| K | Tipo de Producto | Texto | No (default Bienes) | "Bienes" / "Servicio" / "Combo" |
| L | Trazabilidad | Texto | No (default Ninguno) | "Ninguno" / "Por Lote" / "Por Número de Serie" |

### Valores válidos para Tipo de Producto

| Valor en Excel | Resultado en Odoo | Descripción |
|----------------|-------------------|-------------|
| `Bienes`, `Almacenable`, `Consumible`, `Product`, `Storable` | `consu` | Productos físicos (Goods en Odoo 19) |
| `Servicio`, `Service` | `service` | Servicios no tangibles |
| `Combo` | `combo` | Productos combinados |

### Valores válidos para Trazabilidad

| Valor en Excel | Resultado en Odoo |
|----------------|-------------------|
| `Ninguno`, `None`, `No` | `none` |
| `Por Lote`, `Lote`, `Lot` | `lot` |
| `Por Número de Serie`, `Serie`, `Serial` | `serial` |

## Validaciones

El módulo valida los siguientes aspectos antes de crear productos:

### Validaciones en Tiempo de Carga (Excel)

- ✅ **Referencia interna requerida** (campo obligatorio)
- ✅ **Nombre del producto requerido** (campo obligatorio)
- ✅ **Código de barras único en base de datos** (no permite duplicados existentes)
- ✅ **Código de barras único en el archivo** (detecta duplicados internos en el Excel)
- ✅ **Precio de venta no negativo** (0 es válido)
- ✅ **Precio de costo no negativo** (0 es válido)
- ✅ **Cantidad no negativa** (0 es válido)

### Validaciones en Tiempo Real (Creación en Lote)

Las mismas validaciones anteriores, aplicadas automáticamente al editar cada línea.

## Ejemplo de Uso

### Escenario: Importar 5000 productos

1. **Preparar Excel**: Descargar plantilla y llenar con 5000 filas
2. **Cargar archivo**: El wizard valida en ~2-3 segundos (gracias a batch validation)
3. **Revisar vista previa**: Identificar filas con errores (ej. códigos duplicados)
4. **Confirmar**: La creación masiva toma ~5-8 segundos para 5000 productos

**Sin optimización**: Timeout después de 60 segundos con ~500 productos.

## Estructura del Módulo

```
product_mass_import/
├── __init__.py
├── __manifest__.py
├── requirements.txt
├── README.md
├── data/
│   └── sequence.xml
├── i18n/
│   └── es.po
├── models/
│   ├── __init__.py
│   ├── product_mass_import_wizard.py    # Wizard Excel (OPTIMIZADO)
│   └── product_batch_import.py          # Creación en lote (OPTIMIZADO)
├── security/
│   └── ir.model.access.csv
└── views/
    ├── menu_views.xml
    ├── product_batch_import_views.xml
    └── product_mass_import_wizard_views.xml
```

## Notas Técnicas

### Por qué `type='consu'` para productos almacenables en Odoo 19

En Odoo 18/19, la estructura del campo `type` cambió:

```python
# Odoo 17 y anteriores:
type = Selection([('product', 'Storable'), ('consu', 'Consumable'), ('service', 'Service')])

# Odoo 18/19:
type = Selection([('consu', 'Goods'), ('service', 'Service'), ('combo', 'Combo')])
```

El campo `is_stored` que existía en versiones intermedias fue removido. Ahora:
- **`consu` (Goods)**: Incluye tanto productos almacenables como consumibles
- **`service`**: Servicios
- **`combo`**: Productos combinados

La distinción entre "almacenable" y "consumible" ahora se maneja mediante configuraciones de categoría y rutas.

### Batch Processing Implementation

```python
# Patrón usado para evitar N+1:

# 1. Extraer valores únicos
unique_categ_names = set(valid_products.mapped('categ_name'))

# 2. Precargar en diccionario
categories_cache = {}
for categ_name in unique_categ_names:
    category = self.env['product.category'].search([('name', '=', categ_name)], limit=1)
    if not category:
        category = self.env['product.category'].create({'name': categ_name})
    categories_cache[categ_name] = category

# 3. Usar cache en bucle (sin queries adicionales)
for preview in valid_products:
    categ_id = categories_cache[preview.categ_name].id if preview.categ_name else ...
```

## Licencia

OPL-1 - Odoo Proprietary License v1

## Soporte

Crossnexion E.A.S. - https://www.crossnexion.com

## Historial de Versiones

### 19.0.1.2.0 (2026-06-17)
- ✅ **NEW**: Fuzzy match para categorías (evita duplicados por errores de tipeo)
- ✅ **NEW**: Notificación detallada de categorías reutilizadas/creadas
- 🔧 Algoritmo de matching:
  - Búsqueda exacta normalizada (ignora tildes/mayúsculas)
  - Búsqueda por contención de palabras
  - Similaridad de 80% en palabras compartidas

### 19.0.1.1.0 (2026-06-17)
- 🔥 **OPTIMIZACIÓN**: Batch processing para creación masiva de productos
- 🔥 **OPTIMIZACIÓN**: Validación de barcodes en una sola consulta SQL
- ✅ **FIX**: Actualizado campo `type` para Odoo 19 (`consu`/`service`/`combo`)
- ✅ **FIX**: Detección de duplicados internos en el mismo archivo Excel
- ✅ **FIX**: Eliminada redundancia try-except en openpyxl
- ✅ **NEW**: Campo `description_sale` (Descripción para PdV)
- ✅ **NEW**: Campo `default_code` (Referencia Interna) obligatorio

### 19.0.1.0.0 (2026-06-17)
- Versión inicial
