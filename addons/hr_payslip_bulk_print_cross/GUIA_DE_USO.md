# Impresión Masiva de Recibos de Nómina - Crossnexion

**Módulo:** `hr_payslip_bulk_print_cross`
**Versión:** 18.0.1.0.0
**Compatible con:** Odoo 18 Community y Enterprise
**Autor:** Crossnexion / Orlando Lauseker

---

## 1. ¿Qué hace este módulo?

Permite **seleccionar varios recibos de nómina (`hr.payslip`)** desde
la vista de lista, desde un lote (`hr.payslip.run`) o desde el
formulario de un recibo, y **generar un archivo ZIP** con un PDF
separado por cada recibo (también admite un PDF consolidado opcional).

Está pensado para los flujos de trabajo de Paraguay donde el área de
RR.HH. necesita imprimir/distribuir las planillas de pago según los
formatos exigidos por el MTESS (Ministerio de Trabajo, Empleo y
Seguridad Social) y el Código Laboral (Ley 213/93, art. 240).

## 2. Instalación

1. Copiar la carpeta `hr_payslip_bulk_print_cross/` dentro del
   directorio de **addons** de Odoo (ejemplo: `extra-addons/`).
2. Reiniciar el servicio de Odoo.
3. Ir a **Aplicaciones**, presionar *Actualizar Lista de Aplicaciones*.
4. Buscar **"Impresión Masiva de Recibos"** e instalar.

> Dependencias: `base`, `hr`, `hr_payroll`. Opcional pero recomendado:
> `l10n_py_hr_payroll_report` (para usar el reporte funcionario PY).

## 3. Cómo se usa

### 3.1 Desde la lista de Recibos de Nómina

1. Ir a **Nómina ➜ Recibos de Nómina**.
2. Marcar con el checkbox los recibos que se desea imprimir.
3. Click en el botón **Acción ➜ Imprimir Recibos en Masa**.
4. En el wizard:
   - Elegir la **plantilla de reporte** (Recibo Funcionario, Recibo IPS,
     Estándar de Odoo, o **Recibo de Pago - Formato MTESS**).
   - Elegir el **formato de salida**:
     - *PDFs separados en ZIP (uno por recibo)* ← recomendado.
     - *Un único PDF consolidado*.
   - Filtro opcional por **estado** (Borrador, Por Verificar, Hecho).
5. Click en **Generar Archivo**.
6. Click en **Descargar**.

### 3.2 Desde un Lote de Nómina (Batch)

1. Ir a **Nómina ➜ Lotes de Recibos**.
2. Abrir un lote (o seleccionar varios desde la lista).
3. Botón **Imprimir Recibos del Lote** (o **Acción ➜ Imprimir Recibos en Masa**).
4. Continuar igual que en 3.1 desde el paso 4.

### 3.3 Desde el formulario de un recibo individual

1. Abrir cualquier recibo.
2. Botón **Imprimir (Lote)** en la cabecera. (Nota: lo recomendable es
   seleccionar varios desde la lista para aprovechar la impresión masiva.)

## 4. Reporte MTESS incluido

El módulo agrega un reporte propio: **"Recibo de Pago - Formato MTESS"**
con el siguiente contenido mínimo:

- Identificación del empleador (Razón social, RUC, Patronal IPS,
  domicilio).
- Identificación del trabajador (Nombre, C.I., Nº IPS, Cargo, fecha
  de ingreso).
- Período liquidado (desde / hasta).
- Detalle de **haberes y descuentos** (código, concepto, cantidad,
  haber, descuento).
- **Total imponible** y **Líquido a percibir**.
- Espacio para **firma del trabajador**, **firma del empleador** y
  **lugar/fecha**.

Conforme al **art. 240 de la Ley 213/93** (Código Laboral) y los
formatos del MTESS.

## 5. Estructura de nombres de archivo

Cada PDF dentro del ZIP se nombra así:

```
Recibo_<Nombre_Empleado>_<CI>_<AAAA_MM>_<NumeroRecibo>.pdf
```

Ejemplo: `Recibo_Juan_Perez_3456789_2026_04_SLIP00045.pdf`

## 6. Permisos

- Usuarios del grupo **Empleado de Nómina** (`hr_payroll.group_hr_payroll_user`)
  pueden ejecutar la impresión masiva.
- Usuarios del grupo **Responsable de Nómina** (`hr_payroll.group_hr_payroll_manager`)
  también, con todos los permisos.

## 7. Solución de problemas

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| El ZIP descarga vacío | Filtro de estado descartó todos los recibos | Cambiar el filtro a "Todos los estados" |
| El PDF muestra "False" en algunos campos | Faltan datos del empleado o empresa (RUC, IPS) | Completar en *Empleados* y *Compañía* |
| No aparece el botón en lotes | Caché del navegador | Recargar con Ctrl+F5 y actualizar el módulo |
| Error al renderizar uno de los recibos | Plantilla incompatible con el recibo | Revisar log del servidor; revisar estructura salarial |

## 8. Soporte

Cualquier ajuste adicional (campos extra, otra plantilla MTESS,
combinaciones con otros reportes existentes), contactar a Crossnexion.
