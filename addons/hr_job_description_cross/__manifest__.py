# -*- coding: utf-8 -*-
{
    'name': 'Manual de Funciones por Puesto (Crossnexion)',
    'version': '18.0.1.0.22',
    'category': 'Human Resources',
    'summary': 'Manual de Funciones con catalogos, workflow, codigo unico, '
               'exportacion a Word, control de vencimiento (proxima '
               'revision +3 meses) y auto-instalacion de dependencias.',
    'description': """
v18.0.1.0.22 - Fix: upgrade bloqueado por manual aprobado
==========================================================

* La proteccion de campos del manual aprobado ya no bloquea recomputes
  internos ni migraciones (solo bloquea modificacion de contenido visible).
* Soporte de context skip_manual_lock=True para bypass en migraciones.

v18.0.1.0.21 - Fix: filtro Vencidos en busqueda
================================================

* Agregado metodo _search_manual_is_overdue para que el campo computed
  pueda usarse en filtros de busqueda y dominios.

v18.0.1.0.20 - Bloqueo total cuando aprobado
==============================================

* Cuando manual_state='approved', NINGUN campo del manual es editable
* Para modificar un manual aprobado, hay que usar el boton "Reabrir (Borrador)"
* El boton "Reabrir" solo aparece para usuarios del grupo "Aprobador"
* Mensaje claro de bloqueo: "Manual APROBADO y BLOQUEADO"

v18.0.1.0.19 - Metadata extendida en PDF y Word
================================================

* Campo Creador del Documento (auto-asignado al crear)
* Fecha de proxima revision (auto: creacion + 3 meses)
* Indicador de VENCIDO si la fecha de proxima revision esta atrasada
* Banner rojo en formulario si esta vencido
* Filtros "Vencidos" / "Vigentes" en busqueda
* Tabla metadata completa en PDF y Word: codigo, estado, fecha creacion,
  creador, fecha envio revision, aprobador, proxima revision, fecha aprobacion
* Al reabrir un manual aprobado, se reinicia tambien el contador de 3 meses

v18.0.1.0.18 - Auto-instalacion de python-docx
==============================================

* Auto-instalacion de python-docx via pip al instalar/actualizar el modulo

v18.0.1.0.17 - Codigo unico secuencial + Exportar a Word
========================================================

* Codigo unico secuencial por manual (MF/AAAA/NNNNN)
* Revision automatica (00 -> 01 -> 02...) al reabrir manuales aprobados
* Exportar manual a documento Word (.docx)

Funcionalidades base
====================

* Estados: Borrador -> En Revision -> Aprobado / Rechazado
* Workflow con permisos por grupo "Aprobador de Manual de Funciones"
* Vistas: kanban por estado/departamento, lista, formulario
* Catalogo de Funciones, Niveles de Formacion, Habilidades nativas
* Reporte PDF profesional con logo, secciones y firmas
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_skills'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/education_levels.xml',
        'data/function_catalog.xml',
        'views/hr_job_views.xml',
        'report/report_hr_job_manual.xml',
        'report/report_hr_job_manual_templates.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'post_load': 'post_load',
}
