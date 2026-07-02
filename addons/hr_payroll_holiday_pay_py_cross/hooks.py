# -*- coding: utf-8 -*-
"""
Post-install hook: crea las reglas salariales PY_FERIADO_DIA y
PY_FERIADO_NOCHE en cada estructura salarial existente.

Conforme al Codigo Laboral del Paraguay (Ley 213/93, art. 215):
- Trabajador que labora en feriado: pago doble (recargo del 100%).
- En franja nocturna se aplica recargo adicional sobre la nocturna ya
  recargada (~30%).
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    Rule = env['hr.salary.rule'].sudo()
    Structure = env['hr.payroll.structure'].sudo()
    structures = Structure.search([])

    category = env.ref(
        'hr_payroll_holiday_pay_py_cross.hr_salary_rule_category_py_feriado',
        raise_if_not_found=False,
    )
    if not category:
        _logger.warning(
            'Categoria PY_FERIADO no encontrada; abortando creacion de reglas.'
        )
        return

    # Bonificacion DIURNA por feriado trabajado: 100% adicional
    # (ej: trabajador cobra el dia normal + 100% extra sobre las horas)
    diurnal_amount = (
        "# 100% adicional por hora diurna trabajada en feriado.\n"
        "# Tarifa hora = salario base / 24 dias / 8 horas (convencion PY)\n"
        "horas = payslip.hours_holiday_day_worked or 0.0\n"
        "tarifa = (contract.wage or 0.0) / 24.0 / 8.0\n"
        "result = horas * tarifa * 1.0  # 1.0 = 100% recargo\n"
    )
    diurnal_condition = "result = (payslip.hours_holiday_day_worked or 0) > 0"

    # Bonificacion NOCTURNA por feriado trabajado: 100% adicional sobre
    # tarifa nocturna (que ya tiene 30% extra) -> efecto ~160% adicional
    nocturnal_amount = (
        "# 100% adicional sobre tarifa nocturna (que ya incluye 30% extra)\n"
        "horas = payslip.hours_holiday_night_worked or 0.0\n"
        "tarifa = (contract.wage or 0.0) / 24.0 / 8.0\n"
        "tarifa_nocturna = tarifa * 1.3  # 30% extra por horario nocturno\n"
        "result = horas * tarifa_nocturna * 1.0  # 100% recargo\n"
    )
    nocturnal_condition = "result = (payslip.hours_holiday_night_worked or 0) > 0"

    rules_def = [
        {
            'name': 'Bonificacion diurna por feriado trabajado',
            'code': 'PY_FERIADO_DIA',
            'sequence': 110,
            'condition_python': diurnal_condition,
            'amount_python_compute': diurnal_amount,
        },
        {
            'name': 'Bonificacion nocturna por feriado trabajado',
            'code': 'PY_FERIADO_NOCHE',
            'sequence': 111,
            'condition_python': nocturnal_condition,
            'amount_python_compute': nocturnal_amount,
        },
    ]

    created = 0
    for struct in structures:
        for rdef in rules_def:
            existing = Rule.search([
                ('struct_id', '=', struct.id),
                ('code', '=', rdef['code']),
            ], limit=1)
            if existing:
                continue
            Rule.create({
                'name': rdef['name'],
                'code': rdef['code'],
                'sequence': rdef['sequence'],
                'category_id': category.id,
                'struct_id': struct.id,
                'condition_select': 'python',
                'condition_python': rdef['condition_python'],
                'amount_select': 'code',
                'amount_python_compute': rdef['amount_python_compute'],
                'appears_on_payslip': True,
                'active': True,
            })
            created += 1
            _logger.info(
                'Regla %s creada en estructura "%s"', rdef['code'], struct.name
            )
    _logger.info(
        'post_init_hook PY_FERIADO: %d regla(s) creadas en %d estructura(s).',
        created, len(structures),
    )
