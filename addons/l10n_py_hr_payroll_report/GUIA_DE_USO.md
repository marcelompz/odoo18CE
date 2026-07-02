# Guía de Uso - Módulo de Nómina Paraguay para Odoo 18

## Introducción

El módulo **Paraguay - Payroll Reports** (`l10n_py_hr_payroll_report`) es una localización para Odoo 18 que permite gestionar la nómina de empleados en Paraguay según la legislación laboral vigente (Ley 213/93).

### Características Principales

✅ **Estructura salarial paraguaya preconfigurada** con todas las reglas necesarias  
✅ **Cálculo automático de IPS** (9% trabajador, 16.5% patronal)  
✅ **Provisión de aguinaldo y vacaciones** según ley  
✅ **Bonificación familiar** para empleados con dependientes  
✅ **Recibo de pago de funcionario** en formato oficial  
✅ **Planilla IPS** para declaración al Instituto de Previsión Social  
✅ **Exportación bancaria** para pagos masivos  
✅ **Gestión de dependientes** para bonificación familiar  

### Requisitos Previos

- Odoo 18 Enterprise Edition
- Módulo `hr_payroll` instalado
- Módulo `hr_contract` instalado
- Empresa configurada con país: **Paraguay**

---

## Instalación y Configuración Inicial

### 1. Instalación del Módulo

1. **Copiar el módulo** en el directorio de módulos personalizados de Odoo:
   ```
   /ruta/odoo/addons-customize/l10n_py_hr_payroll_report/
   ```

2. **Actualizar la lista de aplicaciones:**
   - Ir a **Aplicaciones** → **Actualizar lista de aplicaciones**

3. **Instalar el módulo:**
   - Buscar "Paraguay - Payroll Reports"
   - Hacer clic en **Instalar**

### 2. Verificar Configuración de la Empresa

1. Ir a **Configuración** → **Usuarios y Compañías** → **Compañías**
2. Seleccionar tu empresa
3. Verificar que el campo **País** esté configurado como **Paraguay**
4. Completar datos de la empresa (RUC, dirección, teléfono, etc.)

### 3. Configurar Calendario de Trabajo

**Ubicación:** Recursos Humanos → Configuración → Calendarios de Trabajo

#### Jornada Diurna (48 horas/semana)
```
Nombre: Jornada Diurna - Paraguay
Horas semanales: 48
Horas diarias: 8
Días laborables: Lunes a Sábado
Horario ejemplo: 08:00 - 17:00 (con 1 hora de almuerzo)
```

#### Jornada Nocturna (42 horas/semana)
```
Nombre: Jornada Nocturna - Paraguay
Horas semanales: 42
Horas diarias: 7
Días laborables: Lunes a Sábado
Horario ejemplo: 20:00 - 04:00 (con 1 hora de descanso)
```

**⚠️ IMPORTANTE:** Asignar el calendario correcto a cada contrato de empleado.

---

## Configuración de Empleados

### 1. Crear un Empleado

**Ubicación:** Empleados → Empleados → Crear

#### Datos Básicos Requeridos:
- **Nombre completo**
- **C.I. N°** (Cédula de Identidad)
- **Dirección**
- **Teléfono**
- **Email** (opcional)

### 2. Configurar Datos IPS

**Ubicación:** En el formulario del empleado, pestaña **Principal**

1. **Número de IPS:**
   - Campo: **Número IPS**
   - Formato: Número de asegurado del IPS
   - **⚠️ IMPORTANTE:** Si el empleado NO tiene número IPS, dejar este campo vacío. El sistema NO calculará aportes IPS si no hay número.

2. **Tipo de Contrato:**
   - Seleccionar el tipo según corresponda (Mensual, Jornal, Comisión)

### 3. Agregar Dependientes (Para Bonificación Familiar)

**Ubicación:** En el formulario del empleado, pestaña **Dependientes**

1. Hacer clic en **Agregar una línea**
2. Completar los datos:
   - **Nombre completo**
   - **C.I. N°**
   - **Fecha de nacimiento**
   - **Parentesco** (Hijo/a, Cónyuge, etc.)
   - **Activo** (marcar si aplica para bonificación)

**Nota:** La bonificación familiar se calcula automáticamente si el empleado tiene dependientes activos menores de 18 años.

### 4. Configurar Cuenta Bancaria

**Ubicación:** En el formulario del empleado, pestaña **Información Personal**

1. Ir a la sección **Información de Contacto**
2. Hacer clic en el contacto asociado (o crear uno nuevo)
3. En el contacto, ir a la pestaña **Información de Contacto**
4. Agregar cuenta bancaria:
   - **Tipo de cuenta:** Cuenta corriente o Caja de ahorro
   - **Número de cuenta:** Número completo de la cuenta bancaria
   - **Banco:** Seleccionar el banco correspondiente

**⚠️ IMPORTANTE:** La cuenta bancaria es necesaria para:
- Exportación bancaria de pagos
- Mostrar en el recibo de pago

---

## Configuración de Contratos

### 1. Crear Contrato de Trabajo

**Ubicación:** Empleados → Contratos → Crear

#### Datos Requeridos:

1. **Empleado:** Seleccionar el empleado
2. **Nombre del contrato:** Ej: "Contrato - Juan Carlos Pérez"
3. **Fecha de inicio:** Fecha de inicio del contrato
4. **Salario:** Salario mensual en Guaraníes
5. **Calendario de trabajo:** Seleccionar el calendario configurado
6. **Tipo de estructura:** Seleccionar según tipo de contrato:
   - **Empleado Mensual - Paraguay** (para empleados mensuales)
   - **Jornalero - Paraguay** (para jornaleros)
   - **Por Comisión - Paraguay** (para empleados a comisión)
7. **Estado:** Cambiar a **En curso** para activar el contrato

### 2. Asignar Estructura Salarial

El módulo crea automáticamente las estructuras salariales:
- **Estructura Salarial Mensual - Paraguay** (`PY_SALARY_STRUCTURE_MONTHLY`)
- **Estructura Salarial Jornal - Paraguay** (`PY_SALARY_STRUCTURE_DAILY`)
- **Estructura Salarial Comisión - Paraguay** (`PY_SALARY_STRUCTURE_COMMISSION`)

La estructura se asigna automáticamente según el tipo de contrato seleccionado.

---

## Configuración de Parámetros de Nómina

**Ubicación:** Nómina → Configuración → Parámetros de regla

### Parámetros Disponibles

| Parámetro | Código | Valor por Defecto | Descripción |
|-----------|--------|-------------------|-------------|
| **IPS Trabajador (%)** | `ips_trabajador_py` | 9.0 | Porcentaje de aporte del trabajador al IPS |
| **IPS Patronal (%)** | `ips_patronal_py` | 16.5 | Porcentaje de aporte patronal al IPS |
| **Divisor Aguinaldo** | `aguinaldo_divisor_py` | 12.0 | Meses para calcular provisión de aguinaldo |
| **Divisor Vacaciones** | `vacaciones_divisor_py` | 12.0 | Meses para calcular provisión de vacaciones |
| **Bonificación Familiar** | `bonificacion_familiar_py` | 100000.0 | Monto fijo de bonificación por dependiente |

### Cómo Configurar

1. Ir a **Nómina → Configuración → Parámetros de regla**
2. Buscar el parámetro por código o nombre
3. Si no existe, crear uno nuevo:
   - **Nombre:** Nombre descriptivo
   - **Código:** Código del parámetro (debe coincidir con la tabla)
   - **Valor:** Valor numérico
4. Guardar

**Nota:** Los valores por defecto están hardcodeados en las reglas salariales, pero puedes crear los parámetros para poder modificarlos desde la interfaz.

---

## Creación y Cálculo de Nóminas

### 1. Crear un Lote de Nómina

**Ubicación:** Nómina → Lotes de nómina → Crear

1. **Nombre del lote:** Ej: "Nómina Enero 2025"
2. **Fecha desde:** Primer día del período
3. **Fecha hasta:** Último día del período
4. **Estado:** Borrador
5. Guardar

### 2. Agregar Recibos al Lote

**Opción A: Agregar empleados individualmente**

1. En el lote, hacer clic en **Agregar una línea**
2. Seleccionar el empleado
3. El sistema creará automáticamente el recibo con:
   - Fechas del período del lote
   - Contrato activo del empleado
   - Estructura salarial asignada

**Opción B: Agregar múltiples empleados**

1. En el lote, hacer clic en **Generar recibos**
2. Seleccionar los empleados o usar filtros
3. Hacer clic en **Generar**

### 3. Configurar Días Trabajados

Para cada recibo en el lote:

1. Abrir el recibo
2. Ir a la pestaña **Días trabajados**
3. Agregar o editar la línea de días trabajados:
   - **Código:** WORK100
   - **Nombre:** Días trabajados
   - **Número de días:** Días trabajados en el período (ej: 30, 24, etc.)
   - **Número de horas:** Días × horas diarias (ej: 30 × 8 = 240)

### 4. Agregar Inputs (Entradas Adicionales)

**Ubicación:** En el recibo, pestaña **Entradas**

Los inputs disponibles son:

- **Horas Extras Diurnas (50%)** (`HE_DIURNA_50`)
- **Horas Extras Diurnas (100%)** (`HE_DIURNA_100`)
- **Horas Extras Nocturnas (50%)** (`HE_NOCTURNA_50`)
- **Horas Extras Nocturnas (100%)** (`HE_NOCTURNA_100`)
- **Comisiones** (`COMISION`)
- **Bonificaciones** (`BONIFICACION`)
- **Aguinaldo** (`AGUINALDO`)
- **Vacaciones** (`VACACIONES`)

**Ejemplo:** Agregar horas extras diurnas al 50%:
1. Hacer clic en **Agregar una línea**
2. **Código:** HE_DIURNA_50
3. **Cantidad:** Número de horas extras
4. **Monto:** Se calculará automáticamente

### 5. Calcular el Recibo

1. En el recibo, hacer clic en **Calcular recibo**
2. El sistema calculará automáticamente:
   - Salario básico
   - Ingresos adicionales (horas extras, comisiones, etc.)
   - Total bruto
   - Deducciones (IPS, otros)
   - Neto a cobrar
   - Provisiones (aguinaldo, vacaciones)
   - Cargas patronales (IPS patronal)

### 6. Verificar Cálculos

**Ubicación:** En el recibo, pestaña **Líneas de salario**

Verificar que aparezcan las siguientes líneas (según corresponda):

**Ingresos:**
- Salario Básico
- Horas Extras (si aplica)
- Bonificación Familiar (si tiene dependientes)
- Comisiones (si aplica)
- Otros ingresos

**Deducciones:**
- IPS Trabajador (9% del total bruto) - Solo si tiene número IPS
- Otras deducciones

**Totales:**
- Total Bruto
- Total Deducciones
- Neto a Cobrar

### 7. Validar y Confirmar

1. Revisar todos los cálculos
2. Hacer clic en **Validar** (cambia el estado a "Verificado")
3. Hacer clic en **Confirmar** (cambia el estado a "Hecho")
4. El recibo queda listo para pagar

### 8. Marcar como Pagado

Una vez realizado el pago:
1. Hacer clic en **Marcar como pagado**
2. El estado cambia a "Pagado"

---

## Generación de Reportes

### 1. Recibo de Pago de Funcionario

**Ubicación:** En el recibo de nómina → Botón **Imprimir** → **Recibo de Pago de Sueldo - Funcionario**

O desde el menú: **Nómina → Recibos de nómina → [Seleccionar recibo] → Imprimir**

#### Contenido del Reporte:

- **Encabezado:** Datos de la empresa (nombre, RUC, dirección)
- **Información del empleado:** Nombre, C.I., cargo, período
- **Haberes (Ingresos):**
  - Salario básico
  - Horas extras
  - Bonificación familiar
  - Comisiones
  - Otros ingresos
- **Descuentos (Deducciones):**
  - IPS trabajador
  - Otras deducciones
- **Totales:**
  - Total haberes
  - Total descuentos
  - Neto a cobrar
- **Información adicional:**
  - Días trabajados
  - Horas trabajadas
  - Método de pago
  - Cuenta bancaria
- **Firmas:** Espacios para firmas del empleado y empleador

**Formato:** PDF según normativa paraguaya (Ley 213/93)

### 2. Planilla IPS

**Ubicación:** Nómina → Lotes de nómina → [Seleccionar lote] → **Exportar Planilla IPS**

O desde múltiples recibos:
1. Seleccionar varios recibos en estado "Hecho" o "Pagado"
2. Acción → **Exportar Planilla IPS**

#### Contenido de la Planilla:

- **Ide Asecot:** Número de identificación del asegurado (IPS)
- **Nro Cic:** Número de CIC (Cédula de Identidad Civil)
- **Asegurado:** Nombre completo del empleado
- **Salario Real:** Salario total del período
- **Dias:** Días trabajados
- **Salario Imponible:** Base imponible para IPS
- **Mov:** Movimiento (Alta, Baja, Modificación)

**Formato:** Excel (.xlsx) listo para importar en el sistema del IPS

**⚠️ IMPORTANTE:** Solo se incluyen empleados con número IPS configurado.

---

## Exportación de Datos

### 1. Exportación Bancaria

**Ubicación:** Nómina → Lotes de nómina → [Seleccionar lote] → **Exportar Pagos Bancarios**

#### Configuración del Wizard:

1. **Lote de nómina:** Seleccionado automáticamente
2. **Fecha a pagar:** Fecha en que se realizará el pago
3. **Concepto:** Concepto del pago (por defecto: "ACREDITACION")
4. **Cuenta débito:** Número de cuenta de la empresa
5. **Banco cliente:** Nombre del banco (ej: "Itau")
6. **Tipo de pago:** Tipo de operación (por defecto: "Credito en cuenta")
7. **Moneda:** Moneda del pago (por defecto: "Guaranies")
8. **Comentario:** Comentario adicional (opcional)
9. **Referencia operación:** Referencia de la operación (opcional)

#### Generar Archivo:

1. Hacer clic en **Generar archivo**
2. El sistema generará un archivo Excel (.xlsx) con:
   - Datos de cada empleado
   - Número de cuenta bancaria
   - Monto a pagar (neto a cobrar)
   - Información de la transacción
3. Descargar el archivo
4. Enviar al banco para procesar los pagos

**⚠️ REQUISITOS:**
- Todos los empleados deben tener cuenta bancaria configurada
- Los recibos deben estar en estado "Hecho" o "Pagado"

### 2. Exportación Planilla IPS

**Ubicación:** Nómina → Lotes de nómina → [Seleccionar lote] → **Exportar Planilla IPS**

1. Seleccionar el lote de nómina
2. Hacer clic en **Generar archivo**
3. El sistema generará un archivo Excel con la planilla IPS
4. Descargar y enviar al IPS

---

## Conceptos Específicos de Paraguay

### 1. IPS (Instituto de Previsión Social)

#### Aporte del Trabajador (9%)
- Se calcula sobre el **total bruto** (salario básico + adicionales)
- Solo se calcula si el empleado tiene **número IPS** configurado
- Si no hay número IPS, NO se calcula el aporte

#### Aporte Patronal (16.5%)
- Se calcula sobre el **total bruto**
- Es una carga patronal (no se descuenta al empleado)
- Aparece en los cálculos pero NO en el recibo del empleado

### 2. Aguinaldo

- **Provisión mensual:** Se calcula como `Salario básico / 12`
- Se acumula mes a mes
- Se paga en diciembre según ley

### 3. Vacaciones

- **Provisión mensual:** Se calcula como `Salario básico / 12`
- Se acumula mes a mes
- Se paga cuando el empleado toma vacaciones

### 4. Bonificación Familiar

- **Monto:** 100,000 Guaraníes por dependiente (configurable)
- **Requisitos:**
  - Empleado debe tener dependientes activos
  - Dependientes menores de 18 años
- Se calcula automáticamente si se cumplen los requisitos

### 5. Horas Extras

#### Horas Extras Diurnas
- **50%:** Primeras horas extras del día
- **100%:** Horas extras adicionales o domingos/festivos

#### Horas Extras Nocturnas
- **50%:** Primeras horas extras nocturnas
- **100%:** Horas extras nocturnas adicionales

**Cálculo:** Se calcula sobre el valor hora del empleado según su salario y calendario.

### 6. Estructura Salarial

El módulo incluye tres tipos de estructuras:

1. **Mensual:** Para empleados con salario mensual fijo
2. **Jornal:** Para empleados que cobran por día trabajado
3. **Comisión:** Para empleados que cobran por comisiones

---

## Solución de Problemas Comunes

### Problema 1: "El campo line_ids_filtered no existe"

**Solución:** Actualizar el módulo. Este campo fue eliminado y ahora se usa un dominio en el campo `line_ids` existente.

### Problema 2: "IPS no se calcula aunque el empleado tiene número IPS"

**Verificaciones:**
1. Verificar que el número IPS esté configurado en el empleado (no vacío)
2. Verificar que el recibo esté calculado
3. Verificar que el empleado tenga contrato activo
4. Recalcular el recibo

### Problema 3: "Bonificación familiar no aparece"

**Verificaciones:**
1. Verificar que el empleado tenga dependientes configurados
2. Verificar que los dependientes estén marcados como "Activos"
3. Verificar que los dependientes sean menores de 18 años
4. Recalcular el recibo

### Problema 4: "Total de Salarios en Guaraníes aparece como item en el recibo"

**Solución:** Este es un campo de cálculo interno. Debe tener `appears_on_payslip = False`. Actualizar el módulo y recalcular los recibos.

### Problema 5: "Error al generar exportación bancaria: faltan cuentas bancarias"

**Solución:**
1. Verificar que todos los empleados tengan cuenta bancaria configurada
2. Verificar que la cuenta bancaria tenga número de cuenta
3. Configurar las cuentas faltantes y volver a intentar

### Problema 6: "Error: unexpected indent en reglas salariales"

**Solución:** Este error ya fue corregido. Actualizar el módulo a la última versión.

### Problema 7: "Los días trabajados no se calculan automáticamente"

**Solución:** Los días trabajados deben configurarse manualmente en cada recibo. El sistema no los calcula automáticamente.

### Problema 8: "El recibo muestra líneas duplicadas"

**Solución:** Actualizar el módulo. Se implementó un filtro que elimina duplicados priorizando reglas paraguayas (PY_*).

---

## Datos de Demostración

El módulo incluye un wizard para crear datos de demostración:

**Ubicación:** Nómina → Configuración → Crear Payslips de Demostración

Este wizard crea:
- 2 empleados de ejemplo
- Contratos activos
- Cuentas bancarias
- Dependientes (para bonificación familiar)
- Lote de nómina con recibos calculados


## Soporte y Contacto

**Autor:** Ing. Daril Diaz

**Versión:** 18.0.1.0.0

**Licencia:** LGPL-3

---

## Notas Legales

Este módulo está diseñado para cumplir con:
- **Ley 213/93** - Código del Trabajo de la República del Paraguay
- **Decreto 4951/2013** - Reglamentación de la Ley 213/93



### Versión 18.0.1.0.0
- ✅ Estructura salarial paraguaya completa
- ✅ Cálculo automático de IPS (trabajador y patronal)
- ✅ Provisión de aguinaldo y vacaciones
- ✅ Bonificación familiar
- ✅ Recibo de pago de funcionario
- ✅ Planilla IPS
- ✅ Exportación bancaria
- ✅ Gestión de dependientes
- ✅ Filtrado de líneas de totales en recibos
- ✅ Corrección de errores de indentación en reglas salariales
- ✅ Validación de número IPS antes de calcular aportes

