# -*- coding: utf-8 -*-
"""Reglas salariales Paraguay (Crossnexion)."""
import logging

_logger = logging.getLogger(__name__)


def _get_or_skip(env, code):
    return env['hr.salary.rule.category'].sudo().search(
        [('code', '=', code)], limit=1
    )


def _attachment_sum_code(keywords, sign=1):
    keywords_repr = repr([k.lower() for k in keywords])
    sign_op = "+" if sign > 0 else "-"
    return (
        "kws = " + keywords_repr + "\n"
        "total = 0.0\n"
        "atts = employee.salary_attachment_ids if 'salary_attachment_ids' in employee._fields else False\n"
        "if atts:\n"
        "    for att in atts:\n"
        "        if att.state != 'open':\n"
        "            continue\n"
        "        desc = (att.description or '').lower()\n"
        "        if not any(k in desc for k in kws):\n"
        "            continue\n"
        "        if att.date_start and att.date_start > payslip.date_to:\n"
        "            continue\n"
        "        if att.date_end and att.date_end < payslip.date_from:\n"
        "            continue\n"
        "        total += att.monthly_amount or 0.0\n"
        "result = " + sign_op + " total\n"
    )


def _attachment_condition_code(keywords):
    keywords_repr = repr([k.lower() for k in keywords])
    return (
        "kws = " + keywords_repr + "\n"
        "result = False\n"
        "atts = employee.salary_attachment_ids if 'salary_attachment_ids' in employee._fields else False\n"
        "if atts:\n"
        "    for att in atts:\n"
        "        if att.state != 'open':\n"
        "            continue\n"
        "        desc = (att.description or '').lower()\n"
        "        if not any(k in desc for k in kws):\n"
        "            continue\n"
        "        if att.date_start and att.date_start > payslip.date_to:\n"
        "            continue\n"
        "        if att.date_end and att.date_end < payslip.date_from:\n"
        "            continue\n"
        "        result = True\n"
        "        break\n"
    )


REPORT_DAY_HOURS_CODE = (
    "Report = payslip.env['hr.attendance.daily.report'].sudo()\n"
    "rows = Report.search([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('date', '>=', payslip.date_from),\n"
    "    ('date', '<=', payslip.date_to),\n"
    "    ('absence_status', '!=', 'rest'),\n"
    "])\n"
    "horas = sum(rows.mapped('total_extra_day') or [0.0])\n"
)

REPORT_NIGHT_HOURS_CODE = (
    "Report = payslip.env['hr.attendance.daily.report'].sudo()\n"
    "rows = Report.search([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('date', '>=', payslip.date_from),\n"
    "    ('date', '<=', payslip.date_to),\n"
    "    ('absence_status', '!=', 'rest'),\n"
    "])\n"
    "horas = sum(rows.mapped('total_extra_night') or [0.0])\n"
)

HE_DAY_AMOUNT = REPORT_DAY_HOURS_CODE + (
    "tarifa = (contract.wage or 0.0) / 24.0 / 8.0\n"
    "result = horas * tarifa * 1.5\n"
)

HE_NIGHT_AMOUNT = REPORT_NIGHT_HOURS_CODE + (
    "tarifa = (contract.wage or 0.0) / 24.0 / 8.0\n"
    "tarifa_nocturna = tarifa * 1.3\n"
    "result = horas * tarifa_nocturna * 2.0\n"
)

HE_DAY_CONDITION = REPORT_DAY_HOURS_CODE + (
    "result = horas > 0\n"
)

HE_NIGHT_CONDITION = REPORT_NIGHT_HOURS_CODE + (
    "result = horas > 0\n"
)

VAC_CONDITION = (
    "Leave = payslip.env['hr.leave'].sudo()\n"
    "leaves = Leave.search([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('state', '=', 'validate'),\n"
    "    ('date_from', '<=', payslip.date_to),\n"
    "    ('date_to', '>=', payslip.date_from),\n"
    "])\n"
    "result = False\n"
    "for l in leaves:\n"
    "    nm = ((l.holiday_status_id.name or '') + ' ' + (l.name or '')).lower()\n"
    "    if 'vacacion' in nm:\n"
    "        result = True\n"
    "        break\n"
)

VAC_AMOUNT = (
    "Leave = payslip.env['hr.leave'].sudo()\n"
    "leaves = Leave.search([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('state', '=', 'validate'),\n"
    "    ('date_from', '<=', payslip.date_to),\n"
    "    ('date_to', '>=', payslip.date_from),\n"
    "])\n"
    "dias = 0.0\n"
    "for l in leaves:\n"
    "    nm = ((l.holiday_status_id.name or '') + ' ' + (l.name or '')).lower()\n"
    "    if 'vacacion' in nm:\n"
    "        dias += l.number_of_days or 0.0\n"
    "divisor = 30.0\n"
    "ct = contract.contract_type_id\n"
    "if ct and 'cn_is_jornalero' in ct._fields and ct.cn_is_jornalero:\n"
    "    divisor = 26.0\n"
    "salario_diario = (contract.wage or 0.0) / divisor\n"
    "result = dias * salario_diario\n"
)

# Crossnexion: Descuento por FALTAS sin justificar.
# Cuenta dias con absence_status='absence' del Tablero Diario (hr.attendance.daily.report)
# y descuenta el salario diario (basico/30) por cada dia de FALTA.
# Para que esto funcione debe ejecutarse "Recalcular Tablero" antes
# del calculo de nomina, asi el reporte refleja las faltas reales.
FALTAS_CONDITION = (
    "Report = payslip.env['hr.attendance.daily.report'].sudo()\n"
    "n = Report.search_count([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('date', '>=', payslip.date_from),\n"
    "    ('date', '<=', payslip.date_to),\n"
    "    ('absence_status', '=', 'absence'),\n"
    "])\n"
    "result = n > 0\n"
)

FALTAS_AMOUNT = (
    "Report = payslip.env['hr.attendance.daily.report'].sudo()\n"
    "faltas = Report.search_count([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('date', '>=', payslip.date_from),\n"
    "    ('date', '<=', payslip.date_to),\n"
    "    ('absence_status', '=', 'absence'),\n"
    "])\n"
    "divisor = 30.0\n"
    "ct = contract.contract_type_id\n"
    "if ct and 'cn_is_jornalero' in ct._fields and ct.cn_is_jornalero:\n"
    "    divisor = 26.0\n"
    "salario_diario = (contract.wage or 0.0) / divisor\n"
    "result = - faltas * salario_diario\n"
)


def _build_rules_def(cat_basic, cat_alw, cat_ded, cat_net, cat_employer, cat_info=None):
    cat_total = cat_info or cat_alw

    rules_def = [
        {'name': 'Salario Bruto', 'code': 'CN_SALARIO_BRUTO', 'sequence': 5,
         'category_id': cat_basic.id, 'condition_python': 'result = True',
         'amount_python_compute': 'result = contract.wage or 0.0\n',
         'appears_on_payslip': True},
        {'name': 'Bonificacion por responsabilidad', 'code': 'BNR', 'sequence': 10,
         'category_id': cat_alw.id,
         'condition_python': _attachment_condition_code(['responsabilidad']),
         'amount_python_compute': _attachment_sum_code(['responsabilidad']),
         'appears_on_payslip': True},
        {'name': 'Bonificacion extraordinaria', 'code': 'BNEX', 'sequence': 11,
         'category_id': cat_alw.id,
         'condition_python': _attachment_condition_code(['extraordinaria']),
         'amount_python_compute': _attachment_sum_code(['extraordinaria']),
         'appears_on_payslip': True},
        {'name': 'Comision por produccion', 'code': 'CP', 'sequence': 12,
         'category_id': cat_alw.id,
         'condition_python': _attachment_condition_code(['comision', 'produccion']),
         'amount_python_compute': _attachment_sum_code(['comision', 'produccion']),
         'appears_on_payslip': True},
        {'name': 'Bonificacion familiar', 'code': 'BNFM', 'sequence': 13,
         'category_id': cat_alw.id,
         'condition_python': _attachment_condition_code(['familiar']),
         'amount_python_compute': _attachment_sum_code(['familiar']),
         'appears_on_payslip': True},
        {'name': 'Vacaciones', 'code': 'CN_VACACIONES', 'sequence': 20,
         'category_id': cat_alw.id,
         'condition_python': VAC_CONDITION,
         'amount_python_compute': VAC_AMOUNT,
         'appears_on_payslip': True},
        {'name': 'Aguinaldo (provision mensual)', 'code': 'CN_AGUINALDO', 'sequence': 25,
         'category_id': cat_alw.id,
         'condition_python': 'result = (contract.wage or 0) > 0',
         'amount_python_compute': 'bruto = contract.wage or 0.0\nresult = bruto / 12.0\n',
         'appears_on_payslip': True},
        {'name': 'Horas Extras Diurnas', 'code': 'CN_HE_DIA', 'sequence': 30,
         'category_id': cat_alw.id,
         'condition_python': HE_DAY_CONDITION,
         'amount_python_compute': HE_DAY_AMOUNT,
         'appears_on_payslip': True},
        {'name': 'Horas Extras Nocturnas', 'code': 'CN_HE_NOCHE', 'sequence': 31,
         'category_id': cat_alw.id,
         'condition_python': HE_NIGHT_CONDITION,
         'amount_python_compute': HE_NIGHT_AMOUNT,
         'appears_on_payslip': True},
        {'name': 'IPS Trabajador (9%)', 'code': 'CN_IPS_TRAB', 'sequence': 50,
         'category_id': cat_ded.id,
         'condition_python': 'result = (contract.wage or 0) > 0',
         'amount_python_compute': 'bruto = contract.wage or 0.0\nresult = - bruto * 0.09\n',
         'appears_on_payslip': True},
        {'name': 'Descuento por Faltas (sin justificar)', 'code': 'CN_FALTAS',
         'sequence': 55,
         'category_id': cat_ded.id,
         'condition_python': FALTAS_CONDITION,
         'amount_python_compute': FALTAS_AMOUNT,
         'appears_on_payslip': True},
        {'name': 'Anticipo', 'code': 'CN_ANTICIPO', 'sequence': 60,
         'category_id': cat_ded.id,
         'condition_python': _attachment_condition_code(['anticipo']),
         'amount_python_compute': _attachment_sum_code(['anticipo'], sign=-1),
         'appears_on_payslip': True},
        {'name': 'Anticipo Extraordinario', 'code': 'CN_ANTICIPO_EXTRA', 'sequence': 61,
         'category_id': cat_ded.id,
         'condition_python': _attachment_condition_code(['anticipo extraordinario']),
         'amount_python_compute': _attachment_sum_code(['anticipo extraordinario'], sign=-1),
         'appears_on_payslip': True},
        {'name': 'Embargo Judicial', 'code': 'CN_EMBARGO', 'sequence': 62,
         'category_id': cat_ded.id,
         'condition_python': _attachment_condition_code(['embargo']),
         'amount_python_compute': _attachment_sum_code(['embargo'], sign=-1),
         'appears_on_payslip': True},
        {'name': 'Prestamo', 'code': 'CN_PRESTAMO', 'sequence': 63,
         'category_id': cat_ded.id,
         'condition_python': _attachment_condition_code(['prestamo']),
         'amount_python_compute': _attachment_sum_code(['prestamo'], sign=-1),
         'appears_on_payslip': True},
        {'name': 'Otros descuentos', 'code': 'CN_OTROS_DESC', 'sequence': 64,
         'category_id': cat_ded.id,
         'condition_python': _attachment_condition_code(['otros descuentos']),
         'amount_python_compute': _attachment_sum_code(['otros descuentos'], sign=-1),
         'appears_on_payslip': True},
        {'name': 'Ingreso Total', 'code': 'CN_INGRESO_TOTAL', 'sequence': 150,
         'category_id': cat_total.id, 'condition_python': 'result = True',
         'amount_python_compute': (
             "bruto = categories['BASIC']\n"
             "alw = categories['ALW']\n"
             "feriado = categories['PY_FERIADO']\n"
             "result = bruto + alw + feriado\n"
         ),
         'appears_on_payslip': True},
        {'name': 'Salario Neto', 'code': 'CN_SALARIO_NETO', 'sequence': 200,
         'category_id': cat_net.id, 'condition_python': 'result = True',
         'amount_python_compute': (
             "bruto = categories['BASIC']\n"
             "alw = categories['ALW']\n"
             "ded = categories['DED']\n"
             "feriado = categories['PY_FERIADO']\n"
             "result = bruto + alw + ded + feriado\n"
         ),
         'appears_on_payslip': True},
    ]

    if cat_employer:
        rules_def.append({
            'name': 'IPS Patronal (16,5%)', 'code': 'CN_IPS_PATRONAL', 'sequence': 300,
            'category_id': cat_employer.id,
            'condition_python': 'result = (contract.wage or 0) > 0',
            'amount_python_compute': 'bruto = contract.wage or 0.0\nresult = bruto * 0.165\n',
            'appears_on_payslip': True,
        })
    return rules_def


def pre_init_hook(env):
    """Pre-init hook:
    1) Crea la columna cn_is_jornalero en hr_contract_type si no existe.
    2) Si existe la columna obsoleta cn_wage_calc en hr_contract, la elimina.
    Esto garantiza que el modulo cargue sin errores de schema desfasado.
    """
    env.cr.execute("""
        ALTER TABLE hr_contract_type
        ADD COLUMN IF NOT EXISTS cn_is_jornalero BOOLEAN DEFAULT FALSE
    """)
    # Limpiar campo obsoleto de versiones anteriores (no critico si falla)
    try:
        env.cr.execute("""
            ALTER TABLE hr_contract DROP COLUMN IF EXISTS cn_wage_calc
        """)
    except Exception:
        pass
    _logger.info('pre_init_hook: schema actualizado para Crossnexion PY rules')


def _seed_contract_types(env):
    """Marca como jornalero los tipos de contrato cuyo nombre sugiere
    contratacion temporal/jornalera. Solo si cn_is_jornalero esta False."""
    CT = env['hr.contract.type'].sudo()
    keywords_jornal = ['temporal', 'jornal', 'estudiante', 'becario',
                       'practica', 'tesis', 'temporada']
    for ct in CT.search([]):
        if ct.cn_is_jornalero:
            continue
        nm = (ct.name or '').lower()
        if any(k in nm for k in keywords_jornal):
            ct.cn_is_jornalero = True





def post_init_hook(env):
    _seed_contract_types(env)
    Rule = env['hr.salary.rule'].sudo()
    Structure = env['hr.payroll.structure'].sudo()
    structures = Structure.search([])
    cat_basic = _get_or_skip(env, 'BASIC')
    cat_alw = _get_or_skip(env, 'ALW')
    cat_ded = _get_or_skip(env, 'DED')
    cat_net = _get_or_skip(env, 'NET')
    cat_employer = env.ref(
        'hr_payroll_rules_py_cross.hr_salary_rule_category_cn_py_employer',
        raise_if_not_found=False,
    )
    cat_info = env.ref(
        'hr_payroll_rules_py_cross.hr_salary_rule_category_cn_py_info',
        raise_if_not_found=False,
    )
    if not cat_alw:
        cat_alw = env['hr.salary.rule.category'].sudo().create({
            'name': 'Asignaciones',
            'code': 'ALW',
        })
    if not (cat_basic and cat_ded and cat_net):
        _logger.warning(
            'No se encontraron las categorias estandar BASIC/DED/NET. '
            'Saltando creacion de reglas Crossnexion PY.'
        )
        return

    rules_def = _build_rules_def(
        cat_basic, cat_alw, cat_ded, cat_net, cat_employer, cat_info,
    )

    created = updated = 0
    for struct in structures:
        for rdef in rules_def:
            existing = Rule.search([
                ('struct_id', '=', struct.id),
                ('code', '=', rdef['code']),
            ], limit=1)
            if existing:
                existing.write({
                    'amount_python_compute': rdef['amount_python_compute'],
                    'condition_python': rdef['condition_python'],
                    'category_id': rdef['category_id'],
                    'sequence': rdef['sequence'],
                })
                updated += 1
                continue
            vals = dict(rdef)
            vals.update({
                'struct_id': struct.id,
                'condition_select': 'python',
                'amount_select': 'code',
                'active': True,
            })
            Rule.create(vals)
            created += 1
    _logger.info(
        'post_init_hook: %d reglas creadas, %d actualizadas en %d estructura(s).',
        created, updated, len(structures),
    )
