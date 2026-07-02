# -*- coding: utf-8 -*-
"""Post-init hook: crea la regla salarial CN_ANTICIPO_QUINCENAL en cada
estructura salarial existente. Se ejecuta una sola vez al instalar.

Es necesario hacerlo via hook porque hr.salary.rule.struct_id es NOT NULL
en Odoo 18 Enterprise y no puede declararse en data XML estatico (necesita
saber a que estructura asociarse).
"""
import logging

_logger = logging.getLogger(__name__)


RULE_CODE = 'CN_ANTICIPO_QUINCENAL'
RULE_NAME = 'Anticipo Quincenal (descuento)'
RULE_SEQUENCE = 390

CONDITION_PYTHON = """
# Aplica si hay anticipos quincenales del empleado en el periodo del recibo
result = bool(
    employee and payslip and payslip.date_from and payslip.date_to and
    env['hr.advance'].sudo().search_count([
        ('employee_id', '=', employee.id),
        ('advance_type', '=', 'quincena'),
        ('quincena_date', '>=', payslip.date_from),
        ('quincena_date', '<=', payslip.date_to),
        ('state', 'in', ('paid', 'done', 'closed')),
    ])
)
"""

AMOUNT_PYTHON_COMPUTE = """
# Descuenta del recibo lo ya pagado en quincena
advances = env['hr.advance'].sudo().search([
    ('employee_id', '=', employee.id),
    ('advance_type', '=', 'quincena'),
    ('quincena_date', '>=', payslip.date_from),
    ('quincena_date', '<=', payslip.date_to),
    ('state', 'in', ('paid', 'done', 'closed')),
])
result = - sum(advances.mapped('amount'))
"""


def post_init_hook(env):
    """Crea la regla CN_ANTICIPO_QUINCENAL en cada hr.payroll.structure
    activa, si todavia no existe."""
    Struct = env['hr.payroll.structure'].sudo()
    Rule = env['hr.salary.rule'].sudo()
    category_ded = env.ref('hr_payroll.DED', raise_if_not_found=False)
    if not category_ded:
        _logger.warning(
            "hr_quincena_cross: no se encontro la categoria hr_payroll.DED. "
            "La regla CN_ANTICIPO_QUINCENAL no se podra crear automaticamente."
        )
        return

    structs = Struct.with_context(active_test=False).search([])
    created = 0
    skipped = 0
    for struct in structs:
        existing = Rule.with_context(active_test=False).search([
            ('struct_id', '=', struct.id),
            ('code', '=', RULE_CODE),
        ], limit=1)
        if existing:
            skipped += 1
            continue
        Rule.create({
            'name': RULE_NAME,
            'code': RULE_CODE,
            'sequence': RULE_SEQUENCE,
            'category_id': category_ded.id,
            'struct_id': struct.id,
            'condition_select': 'python',
            'condition_python': CONDITION_PYTHON.strip(),
            'amount_select': 'code',
            'amount_python_compute': AMOUNT_PYTHON_COMPUTE.strip(),
            'appears_on_payslip': True,
            'active': True,
        })
        created += 1
    _logger.info(
        "hr_quincena_cross: regla CN_ANTICIPO_QUINCENAL -> %d creadas, %d ya existian.",
        created, skipped,
    )
