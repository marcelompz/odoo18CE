# -*- coding: utf-8 -*-
"""Hook para cargar automaticamente los feriados nacionales de Paraguay
en el calendario laboral de cada empresa al instalar/actualizar el modulo.

Crea registros en resource.calendar.leaves SIN resource_id (es decir,
feriados globales para todos los empleados de ese calendario).
"""
from datetime import date, datetime, time, timedelta

from odoo.exceptions import ValidationError


def _easter_date(year):
    """Calculo del Domingo de Pascua (algoritmo de Gauss/Meeus)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _py_holidays_for_year(year):
    """Lista de tuplas (fecha, nombre) con los feriados oficiales de Paraguay."""
    easter = _easter_date(year)
    holy_thursday = easter - timedelta(days=3)
    good_friday = easter - timedelta(days=2)

    return [
        (date(year, 1, 1),   'Anio Nuevo'),
        (date(year, 3, 1),   'Dia de los Heroes (Cerro Cora)'),
        (holy_thursday,      'Jueves Santo'),
        (good_friday,        'Viernes Santo'),
        (date(year, 5, 1),   'Dia del Trabajador'),
        (date(year, 5, 14),  'Vispera del Dia de la Independencia'),
        (date(year, 5, 15),  'Dia de la Independencia Nacional'),
        (date(year, 6, 12),  'Dia de la Paz del Chaco'),
        (date(year, 8, 15),  'Fundacion de Asuncion'),
        (date(year, 9, 29),  'Victoria de Boqueron'),
        (date(year, 12, 8),  'Dia de la Virgen de Caacupe'),
        (date(year, 12, 25), 'Navidad'),
    ]


def _create_one_holiday(Leaves, calendar_id, name, day):
    """Crea (o salta) un unico feriado global. Devuelve 'created'/'skipped'/'failed'.

    Idempotencia: si ya existe CUALQUIER feriado publico (resource_id=False) que
    se solape en esa fecha y calendario, no se crea (independiente del nombre).
    Si la creacion falla por validacion (overlap con uno existente con otro
    nombre), se ignora silenciosamente.
    """
    # Usamos 23:59:00 (no 23:59:59.999999) para evitar que la validacion de
    # Odoo trate el limite del dia como solape con el dia siguiente.
    date_from = datetime.combine(day, time(0, 0, 0))
    date_to = datetime.combine(day, time(23, 59, 0))

    existing = Leaves.search([
        ('calendar_id', '=', calendar_id),
        ('resource_id', '=', False),
        ('date_from', '<=', date_to),
        ('date_to', '>=', date_from),
    ], limit=1)
    if existing:
        return 'skipped'
    try:
        Leaves.create({
            'name': name,
            'calendar_id': calendar_id,
            'resource_id': False,
            'date_from': date_from,
            'date_to': date_to,
        })
        return 'created'
    except ValidationError:
        # Ya existia algun feriado solapado que el search no detecto (p.ej.
        # diferente granularidad horaria). Lo tratamos como ya cargado.
        return 'skipped'
    except Exception:
        return 'failed'


def post_init_load_py_holidays(env):
    """post_init_hook: carga feriados de Paraguay en TODOS los calendarios."""
    Leaves = env['resource.calendar.leaves'].sudo()
    Calendars = env['resource.calendar'].sudo().search([])
    if not Calendars:
        return
    years = range(2024, 2031)
    created = skipped = failed = 0
    for cal in Calendars:
        for year in years:
            for d, name in _py_holidays_for_year(year):
                r = _create_one_holiday(Leaves, cal.id, name, d)
                if r == 'created':
                    created += 1
                elif r == 'skipped':
                    skipped += 1
                else:
                    failed += 1
    return created, skipped, failed
