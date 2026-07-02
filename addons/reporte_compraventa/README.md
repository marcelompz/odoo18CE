# Módulo Reporte Compra-Venta Paraguay

## Descripción
Módulo para generar reportes de Libros IVA Compras y Ventas según la Ley 125/91 de Paraguay.

## Cambios Realizados para Odoo 18

### ✅ Problemas Solucionados

1. **Eliminación de Dependencias Problemáticas**
   - ❌ Removida dependencia de `valente_timbrado`
   - ✅ Mantenidas solo dependencias: `base` y `report_xlsx`

2. **Eliminación de Variables Globales**
   - ❌ Removidas variables globales que causaban conflictos con assets
   - ✅ Implementado código orientado a objetos sin variables globales

3. **Compatibilidad con Odoo 18**
   - ❌ Removidas verificaciones específicas de versiones 15.0 y 16.0
   - ✅ Código compatible con Odoo 18 sin dependencias de versiones específicas

4. **Campos Nativos de Odoo**
   - ❌ Removidas referencias a campos personalizados de timbrado
   - ✅ Uso exclusivo de campos nativos de Odoo

### 📊 Estructura del Reporte

#### Libro IVA Compras
- Fecha del comprobante
- Tipo de comprobante (Factura, NC, ND)
- Timbrado/Establecimiento/Punto de expedición (columna preparada)
- Número de comprobante completo
- Proveedor (razón social)
- RUC del proveedor
- Condición (Contado/Crédito)
- Moneda y tipo de cambio
- Base imponible 10%
- IVA 10%
- Base imponible 5%
- IVA 5%
- Exentas
- Total comprobante
- Crédito fiscal computable

#### Libro IVA Ventas
- Fecha del comprobante
- Tipo de comprobante
- Timbrado/Establecimiento/Punto de expedición (columna preparada)
- Número de comprobante completo
- Cliente (razón social)
- RUC del cliente
- Condición (Contado/Crédito)
- Moneda y tipo de cambio
- Base imponible 10%
- IVA 10%
- Base imponible 5%
- IVA 5%
- Exentas
- Total comprobante
- Débito fiscal

### 🔧 Funcionalidades Implementadas

1. **Cálculo Automático de Impuestos**
   - Detección automática de IVA 10%, 5% y exentas
   - Cálculo correcto de bases imponibles
   - Manejo de notas de crédito con signo negativo

2. **Validaciones**
   - Solo facturas publicadas (state = 'posted')
   - Validación de partners con RUC
   - Manejo de monedas extranjeras con tipo de cambio

3. **Formato Excel**
   - Formato numérico para montos
   - Formato de fecha dd/mm/yyyy
   - Texto con wrap para encabezados largos
   - Totales con formato destacado

### 📁 Estructura del Módulo

```
reporte_compraventa/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── models.py
├── security/
│   └── ir.model.access.csv
├── views/
│   ├── templates.xml
│   └── views.xml
└── README.md
```

### 🚀 Instalación

1. Copiar el módulo a la carpeta `addons` de Odoo
2. Actualizar la lista de módulos en Odoo
3. Instalar el módulo "Libros IVA Venta/Compra"
4. Acceder desde Contabilidad → Libro de Compras/Ventas

### 📋 Dependencias

- `base`: Módulo base de Odoo
- `report_xlsx`: Para generación de reportes Excel

### ⚠️ Notas Importantes

- El campo "Timbrado/Establecimiento/Punto de expedición" está preparado pero vacío
- Se pueden agregar campos personalizados para timbrado si es necesario
- El módulo es compatible con Odoo 18 y versiones posteriores
- No requiere módulos adicionales de timbrado

### 🔄 Mejoras Futuras

- Integración con sistema de timbrado
- Exportación a formatos adicionales (PDF, CSV)
- Filtros adicionales por proveedor/cliente
- Reportes consolidados por período
