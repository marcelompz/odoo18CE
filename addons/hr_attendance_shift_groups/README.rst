============================
HR Attendance Shift Groups
============================

Módulo para Odoo 18 (Enterprise & Community) que extiende ``hr_attendance``
para clasificar automáticamente las horas trabajadas por franjas horarias
según un Grupo de Turno (Operativo / Administrativo) configurable.

Características
===============

* Configuración de Grupos de Turno con franjas horarias parametrizables.
* Soporte de franjas cruzadas de medianoche (ej. 20:00 - 05:59).
* Clasificación automática al registrar check-in / check-out.
* Tablero tipo planilla (vista pivot dinámica) con filtros por período,
  grupo, departamento y empleado.
* Exportación a Excel (.xlsx) replicando el modelo de planilla
  proporcionado.
* Exportación a PDF (QWeb).
* Asignación de turno a nivel de empleado o de contrato (prioridad
  contrato > empleado).
* Compatible con Odoo 18 EE y CE.
* Internacionalización ES / EN.

Instalación
===========

1. Copiar la carpeta ``hr_attendance_shift_groups`` dentro del directorio
   ``addons`` de su instancia Odoo 18.
2. Asegurarse de tener instalada la dependencia Python ``xlsxwriter``::

       pip install xlsxwriter

3. Reiniciar Odoo y actualizar la lista de aplicaciones.
4. Instalar el módulo desde *Aplicaciones*.

Configuración
=============

Al instalar, el módulo precarga dos grupos demo: **Operativo** y
**Administrativo**, con las franjas horarias del PRD.

* *Asistencias > Configuración Turnos > Grupos de Turno* — administrar
  grupos y franjas.
* *Empleado / Contrato* — asignar el grupo correspondiente.
* *Asistencias > Turnos > Tablero por Turnos* — visualizar.
* *Asistencias > Turnos > Exportar Planilla Excel* — generar el archivo.

Modelos
=======

* ``hr.shift.group`` — Grupo de Turno
* ``hr.shift.slot`` — Franja Horaria
* ``hr.attendance.shift.line`` — Línea de distribución por franja
* Herencia: ``hr.attendance``, ``hr.employee``, ``hr.contract``

Tests
=====

Para ejecutar los tests::

    odoo -d <db> --test-enable -i hr_attendance_shift_groups --stop-after-init

Licencia
========

LGPL-3
