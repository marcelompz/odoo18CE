# 📊 Módulo Resolución 77 - Depreciación de Activos Fijos

## 📋 Descripción General
Este módulo implementa el **Cuadro de Depreciación de los Bienes del Activo Fijo** según los requerimientos de la **Resolución General N° 77/2020** de la SET (Subsecretaría de Estado de Tributación) de Paraguay.

## 🎯 Objetivo del Módulo
Permitir a las empresas paraguayas:
- **Registrar** todos los bienes del activo fijo
- **Calcular automáticamente** la depreciación fiscal
- **Generar** el cuadro de depreciación en formato oficial
- **Exportar** los datos a Excel según el formato requerido por la SET
- **Validar** los cálculos del Valor Fiscal Residual

## 🧱 Estructura del Módulo

### 📦 Modelos Principales

#### 1. `resolucion.77.line` - Líneas de Depreciación
**Campos principales:**
- `name`: Descripción del bien
- `codigo`: Código interno del bien
- `fecha_adquisicion`: Fecha de adquisición
- `valor_inicial`: Valor de origen (costo histórico)
- `porcentaje_depreciacion`: % de depreciación anual
- `vida_util`: Vida útil en años
- `categoria_activo`: Categoría del activo fijo

**Campos calculados automáticamente:**
- `depreciacion_anual`: Monto anual de depreciación
- `depreciacion_acumulada`: Depreciación acumulada hasta el cierre
- `valor_fiscal_neto`: Valor contable neto al cierre
- `valor_residual`: Valor residual fiscal (10% por defecto)

#### 2. `resolucion.77.config` - Configuración
Parámetros generales del módulo:
- Porcentajes de depreciación por categoría
- Vida útil por defecto por categoría
- Fecha de cierre fiscal (31/12, 30/04 o 30/06)
- Porcentaje de valor residual

#### 3. `resolucion.77.category.template` - Plantillas de Categorías
Plantillas predefinidas según normativas SET:
- Edificios y Construcciones (2.5% - 40 años)
- Maquinaria y Equipos (10% - 10 años)
- Vehículos (20% - 5 años)
- Muebles y Enseres (10% - 10 años)
- Equipos de Cómputo (25% - 4 años)
- Otros Activos Fijos (10% - 10 años)

## 🔧 Funcionalidades Principales

### ✅ 1. Registro de Bienes
- **Interfaz intuitiva** para registrar bienes del activo fijo
- **Validaciones automáticas** de datos ingresados
- **Categorización** según tipos de activos
- **Adjuntar documentos** de respaldo (facturas, contratos)

### ✅ 2. Cálculos Automáticos
**Fórmulas implementadas:**

```python
# Depreciación Anual
depreciacion_anual = valor_inicial * (porcentaje_depreciacion / 100)

# Depreciación Acumulada
años_transcurridos = (fecha_cierre_fiscal - fecha_adquisicion) / 365.25
años_a_depreciar = min(años_transcurridos, vida_util)
depreciacion_acumulada = depreciacion_anual * años_a_depreciar

# Valor Fiscal Neto
valor_fiscal_neto = valor_inicial - depreciacion_acumulada

# Valor Residual Fiscal
valor_residual = valor_fiscal_neto * (porcentaje_residual / 100)
```

### ✅ 3. Exportación a Excel
- **Formato oficial** de la SET
- **Encabezados corporativos** personalizables
- **Totales automáticos** por columna
- **Nombre de archivo** con fecha: `Cuadro_Depreciacion_Resolucion77_YYYYMMDD_HHMM.xlsx`

### ✅ 4. Importación Masiva (CSV)
- **Wizard de importación** con validaciones
- **Plantilla descargable** con formato correcto
- **Manejo de errores** detallado
- **Estadísticas** de importación

### ✅ 5. Gestión de Estados
- **Bienes activos** vs. **dados de baja**
- **Control de inclusión** en reportes
- **Fechas de baja** registradas
- **Reactivación** de bienes

## 📊 Ejemplo de Uso

### Escenario: Empresa con múltiples activos
```
Bien: Computadora Dell OptiPlex 7090
- Código: EQ-COMP-001
- Fecha adquisición: 01/01/2023
- Valor inicial: Gs. 1.500.000
- Categoría: Equipos de Cómputo
- % Depreciación: 25% anual
- Vida útil: 4 años

Cálculos automáticos (al 31/12/2023):
- Depreciación anual: Gs. 375.000
- Depreciación acumulada: Gs. 375.000 (1 año)
- Valor fiscal neto: Gs. 1.125.000
- Valor residual: Gs. 112.500 (10%)
```

## 🚀 Instalación y Configuración

### Dependencias
- **Odoo 18.0**
- **Python**: `xlsxwriter>=3.0.0`
- **Módulos base**: `account`, `account_asset`

### Pasos de Instalación
1. Copiar módulo a `addons/resolucion_77/`
2. Instalar dependencia Python:
   ```bash
   pip install xlsxwriter>=3.0.0
   ```
3. Actualizar lista de aplicaciones en Odoo
4. Instalar módulo "Resolución 77"

### Configuración Inicial
1. **Ir a**: Resolución 77 → Configuración → Configuración General
2. **Verificar** porcentajes de depreciación por categoría
3. **Configurar** fecha de cierre fiscal de la empresa
4. **Ajustar** porcentaje de valor residual si es necesario

## 📋 Uso del Módulo

### Paso 1: Registrar Bienes
1. **Ir a**: Resolución 77 → Depreciación de Activos → Cuadro de Depreciación
2. **Crear** nuevo registro
3. **Completar** información básica:
   - Descripción del bien
   - Código interno
   - Fecha de adquisición
   - Valor de origen
4. **Seleccionar** categoría de activo
5. **Verificar** porcentajes y vida útil (se completan automáticamente)
6. **Guardar** registro

### Paso 2: Validar Cálculos
- Los campos calculados se actualizan automáticamente
- **Verificar** que los cálculos sean correctos
- **Ajustar** porcentaje residual si es necesario

### Paso 3: Generar Reporte
1. **Ir a**: Resolución 77 → Depreciación de Activos → Exportar a Excel
2. **Configurar filtros**:
   - Ejercicio fiscal
   - Fecha de cierre fiscal
   - Filtros por categoría o fecha
3. **Exportar** a Excel
4. **Revisar** archivo generado

### Paso 4: Importación Masiva (Opcional)
1. **Descargar** plantilla CSV
2. **Completar** datos en Excel/CSV
3. **Usar** wizard de importación
4. **Validar** archivo antes de importar
5. **Revisar** estadísticas de importación

## 📑 Formato de Exportación Excel

### Columnas del Cuadro Oficial
1. **Código**: Código interno del bien
2. **Descripción del Bien**: Nombre descriptivo
3. **Fecha de Adquisición**: DD/MM/YYYY
4. **Valor de Origen**: Costo histórico en guaraníes
5. **% Depreciación Anual**: Porcentaje según normativa
6. **Vida Útil (años)**: Vida útil estimada
7. **Depreciación Acumulada**: Depreciación total hasta la fecha
8. **Valor Fiscal Neto al Cierre**: Valor contable neto
9. **Valor Residual Fiscal**: 10% del valor fiscal neto

### Elementos Adicionales
- **Encabezado**: Nombre y RUC de la empresa
- **Título**: Cuadro de Depreciación - Resolución 77/2020
- **Totales**: Suma de todas las columnas monetarias
- **Metadatos**: Fecha de generación, usuario, sistema

## ⚠️ Validaciones Implementadas

### Validaciones de Datos
- **Porcentaje de depreciación**: Entre 0% y 100%
- **Vida útil**: Mayor a 0 años
- **Valor inicial**: Mayor a 0 guaraníes
- **Fechas**: Adquisición no posterior al cierre fiscal

### Validaciones de Negocio
- **Fechas de cierre**: Solo 31/12, 30/04 o 30/06
- **Cálculos consistentes**: Depreciación no excede valor inicial
- **Estados coherentes**: Bienes dados de baja no activos

## 🛡️ Seguridad

### Grupos de Acceso
- **Usuarios Contables**: Lectura, escritura, creación
- **Gerentes Contables**: Acceso completo + configuración
- **Multi-compañía**: Datos separados por empresa

### Permisos por Modelo
- `resolucion.77.line`: Usuarios y gerentes contables
- `resolucion.77.config`: Solo gerentes contables
- `resolucion.77.category.template`: Solo gerentes contables

## 📞 Soporte Técnico

### Desarrollado por
**Valente Systems EAS – Cristhel Valente**
- **Email**: soporte@valentesystems.com
- **Website**: https://www.valentesystems.com

### Reportar Problemas
Para reportar bugs o solicitar funcionalidades:
1. Contactar al equipo de soporte
2. Incluir descripción detallada del problema
3. Adjuntar logs de errores si es posible
4. Especificar versión de Odoo y del módulo

## 📄 Licencia
Este módulo está licenciado bajo **LGPL-3**

## 🔄 Historial de Versiones

### v18.0.1.0.0 (Inicial)
- ✅ Implementación completa del cuadro de depreciación
- ✅ Cálculos automáticos según normativa SET
- ✅ Exportación a Excel en formato oficial
- ✅ Importación masiva desde CSV
- ✅ Gestión de configuraciones por empresa
- ✅ Validaciones de datos y negocio
- ✅ Compatibilidad total con Odoo 18

---

> **Nota**: Este módulo cumple con los requerimientos de la Resolución General N° 77/2020 de la SET de Paraguay para el período fiscal correspondiente. Se recomienda verificar actualizaciones normativas periódicamente. 