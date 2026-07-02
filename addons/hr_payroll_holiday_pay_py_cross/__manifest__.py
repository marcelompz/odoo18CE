# -*- coding: utf-8 -*-
{
    'name': 'Doble pago feriados Paraguay (Crossnexion)',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Calcula automaticamente el doble pago de horas trabajadas '
               'en feriados (ley Paraguay), diferenciando diurnas y '
               'nocturnas.',
    'description': """
Doble pago feriados Paraguay
============================
Conforme al Codigo Laboral del Paraguay (Ley 213/93, art. 215):

* Trabajador que SI labora en feriado: cobra dia normal + 100% adicional
  (recargo diurno) o + 100% sobre tarifa nocturna que ya tiene 30% extra
  (efectivo ~160%).

Funcionalidad:
* Detecta los feriados (resource.calendar.leaves con work_entry_type
  apropiado) que caen en el periodo del recibo.
* Suma las horas marcadas (hr.attendance) del empleado en esos dias.
* Si el modulo hr_attendance_shift_groups esta instalado, usa los
  campos hours_extra_day / hours_extra_night para diferenciar diurnas
  y nocturnas. Si no, todo se considera diurno.
* Crea automaticamente dos reglas salariales en cada estructura:
   - PY_FERIADO_DIA   (Bonificacion diurna por feriado trabajado)
   - PY_FERIADO_NOCHE (Bonificacion nocturna por feriado trabajado)

Autor: Crossnexion / Orlando Lauseker
""",
    'author': 'Crossnexion',
    'website': 'https://crossnexion.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_attendance', 'hr_payroll', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_salary_rule_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
