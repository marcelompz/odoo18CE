# 🔗 Integración Contable - Resolución 77

## 📋 Resumen de Integración

El módulo **Resolución 77** ahora incluye **integración completa** con el módulo contable de Odoo, permitiendo:

✅ **Crear activos fijos** automáticamente en el sistema contable  
✅ **Generar asientos contables** de depreciación  
✅ **Sincronizar datos** entre Resolución 77 y contabilidad  
✅ **Configurar cuentas contables** específicas  
✅ **Mantener trazabilidad** entre reportes fiscales y contabilidad  

## 🚀 Nuevas Funcionalidades

### 1. **Integración con Activos Fijos**
- **Campo `asset_id`**: Relación directa con `account.asset`
- **Campo `asset_created`**: Indica si el activo fijo fue creado
- **Botón "Crear Activo Fijo"**: Genera automáticamente el activo en contabilidad
- **Botón "Ver Activo Fijo"**: Abre el registro del activo fijo creado

### 2. **Generación de Asientos Contables**
- **Campo `move_ids`**: Lista de asientos contables relacionados
- **Campo `move_count`**: Contador de asientos generados
- **Botón "Generar Asiento"**: Crea asiento de depreciación
- **Botón "Ver Asientos"**: Muestra todos los asientos relacionados

### 3. **Configuración Contable**
- **Cuenta de Activo Fijo**: Para registrar el valor inicial
- **Cuenta de Depreciación Acumulada**: Para depreciación acumulada
- **Cuenta de Gastos de Depreciación**: Para gastos anuales
- **Diario de Depreciación**: Para registrar asientos

## 📊 Flujo de Trabajo Integrado

### Paso 1: Configuración Inicial
1. **Ir a**: Resolución 77 → Configuración → Configuración Contable
2. **Configurar** cuentas contables y diario
3. **Probar** la configuración
4. **Aplicar** a registros existentes (opcional)

### Paso 2: Registrar Bien
1. **Crear** nuevo registro en Resolución 77
2. **Completar** información básica del bien
3. **Configurar** cuentas contables específicas (si es necesario)

### Paso 3: Crear Activo Fijo
1. **Hacer clic** en "Crear Activo Fijo"
2. **Verificar** que se creó correctamente
3. **Revisar** configuración del activo fijo

### Paso 4: Generar Asientos
1. **Hacer clic** en "Generar Asiento"
2. **Revisar** el asiento contable creado
3. **Validar** y publicar el asiento

## 🔧 Configuración de Cuentas

### Cuentas Requeridas

#### 1. **Cuenta de Activo Fijo**
- **Tipo**: Activo Fijo
- **Código típico**: 15xx (según plan contable)
- **Ejemplo**: 1510 - Activos Fijos

#### 2. **Cuenta de Depreciación Acumulada**
- **Tipo**: Activo Fijo
- **Código típico**: 15xx (mismo grupo que activos)
- **Ejemplo**: 1590 - Depreciación Acumulada

#### 3. **Cuenta de Gastos de Depreciación**
- **Tipo**: Gastos
- **Código típico**: 6xx (gastos)
- **Ejemplo**: 6810 - Gastos de Depreciación

### Configuración Automática

El sistema intenta **detectar automáticamente** las cuentas:
- Busca cuentas con códigos típicos (15xx, 6xx)
- Busca cuentas con nombres que contengan "depreciación"
- Usa el diario general por defecto

## 📋 Estructura de Asientos

### Asiento de Depreciación Anual

```
DÉBITO:
- Gastos de Depreciación (6810) = Gs. 375.000

CRÉDITO:
- Depreciación Acumulada (1590) = Gs. 375.000
```

### Campos del Asiento
- **Referencia**: "Depreciación [Nombre del Bien] - [Año]"
- **Fecha**: Fecha de cierre fiscal
- **Diario**: Configurado en el registro
- **Relación**: Campo `resolucion_77_line_id` para trazabilidad

## 🔍 Trazabilidad

### Campos de Relación
- **`resolucion_77_line_id`** en `account.move`
- **`asset_id`** en `resolucion.77.line`
- **`move_ids`** en `resolucion.77.line`

### Reportes de Trazabilidad
- **Vista de asientos**: Desde registro de Resolución 77
- **Vista de activo fijo**: Desde registro de Resolución 77
- **Filtros**: Por estado de integración contable

## ⚙️ Wizard de Configuración

### Funcionalidades
- **Configuración masiva**: Aplicar a múltiples registros
- **Creación automática**: De activos fijos
- **Generación automática**: De asientos contables
- **Validación**: De configuración antes de aplicar

### Opciones Disponibles
- ✅ **Aplicar a Registros Existentes**
- ✅ **Crear Activos Fijos Automáticamente**
- ✅ **Generar Asientos de Depreciación**

## 🛡️ Validaciones y Seguridad

### Validaciones Implementadas
- **Cuentas activas**: Verifica que las cuentas estén activas
- **Misma compañía**: Todas las cuentas deben ser de la misma compañía
- **Diario válido**: Verifica que el diario esté activo
- **Campos requeridos**: Valida configuración completa

### Manejo de Errores
- **Continuación**: Si un registro falla, continúa con los demás
- **Log de errores**: Registra errores para revisión posterior
- **Rollback**: No aplica cambios si hay errores críticos

## 📈 Beneficios de la Integración

### 1. **Automatización**
- Elimina entrada manual de datos
- Reduce errores de transcripción
- Ahorra tiempo en procesos contables

### 2. **Trazabilidad Completa**
- Seguimiento desde reporte fiscal hasta contabilidad
- Auditoría simplificada
- Cumplimiento normativo

### 3. **Consistencia de Datos**
- Misma información en reportes fiscales y contables
- Sincronización automática
- Validaciones cruzadas

### 4. **Eficiencia Operativa**
- Proceso unificado
- Menos duplicación de trabajo
- Reportes integrados

## 🔄 Migración desde Versión Anterior

### Pasos de Migración
1. **Actualizar** el módulo
2. **Ejecutar** wizard de configuración contable
3. **Configurar** cuentas contables
4. **Aplicar** configuración a registros existentes
5. **Crear** activos fijos para registros existentes (opcional)

### Datos Preservados
- ✅ Todos los registros de Resolución 77
- ✅ Configuraciones existentes
- ✅ Reportes generados
- ✅ Documentos adjuntos

## 🆘 Solución de Problemas

### Problema: "Debe configurar la cuenta de activo"
**Solución**: Usar wizard de configuración contable

### Problema: "El activo fijo ya ha sido creado"
**Solución**: Verificar si ya existe el activo fijo

### Problema: "Debe crear el activo fijo primero"
**Solución**: Crear activo fijo antes de generar asientos

### Problema: "Todas las cuentas deben pertenecer a la misma compañía"
**Solución**: Verificar configuración de cuentas por compañía

## 📞 Soporte

Para soporte técnico:
- **Email**: soporte@valentesystems.com
- **Website**: https://www.valentesystems.com
- **Documentación**: Incluida en el módulo

---

**Versión**: 18.0.1.0.0  
**Última actualización**: Integración contable completa  
**Compatibilidad**: Odoo 18.0 