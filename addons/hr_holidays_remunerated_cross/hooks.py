# -*- coding: utf-8 -*-
"""
Post-install hook
=================
Crea la regla salarial PY_DESC_NO_REM en TODAS las estructuras salariales
existentes. En Odoo 18 hr.salary.rule.struct_id es obligatorio, por eso
no podemos crear la regla via XML data sin saber el struct_id.
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    Rule = env['hr.salary.rule'].sudo()
    Structure = env['hr.payroll.structure'].sudo()
    structures = Structure.search([])

    category = env.ref(
        'hr_holidays_remunerated_cross.hr_salary_rule_category_py_no_rem',
        raise_if_not_found=False,
    )
    if not category:
        _logger.warning(
            'Categoria DESC_NO_REM no encontrada; abortando creacion '
            'de la regla PY_DESC_NO_REM.'
        )
        return

    amount_python = (
        "# Salario diario = salario base / 30 (convencion Paraguay)\n"
        "basic = contract.wage or 0.0\n"
        "days = payslip.unremunerated_days or 0.0\n"
        "result = - (basic / 30.0) * days\n"
    )
    condition_python = "result = (payslip.unremunerated_days or 0) > 0"

    created = 0
    for struct in structures:
        existing = Rule.search([
            ('struct_id', '=', struct.id),
            ('code', '=', 'PY_DESC_NO_REM'),
        ], limit=1)
        if existing:
            continue
        Rule.create({
            'name': 'Descuento por dias no remunerados',
            'code': 'PY_DESC_NO_REM',
            'sequence': 100,
            'category_id': category.id,
            'struct_id': struct.id,
            'condition_select': 'python',
            'condition_python': condition_python,
            'amount_select': 'code',
            'amount_python_compute': amount_python,
            'appears_on_payslip': True,
            'active': True,
        })
        created += 1
        _logger.info(
            'Regla PY_DESC_NO_REM creada en estructura "%s"', struct.name
        )

    _logger.info(
        'post_init_hook: %d regla(s) PY_DESC_NO_REM creada(s) en %d '
        'estructura(s) salarial(es).', created, len(structures)
    )
