# -*- coding: utf-8 -*-
"""Aguinaldo Anual Paraguay (Art. 243 Codigo Laboral).

Crea una estructura salarial dedicada "Aguinaldo Anual - Paraguay" con
sus propias reglas y un wizard para generar masivamente los recibos
de aguinaldo en diciembre.

Calculo (Art. 243 CT):
  Aguinaldo = (suma de salarios brutos percibidos en el ano) / 12
  Neto = Aguinaldo - IPS 9% (sobre el bruto del aguinaldo)
"""
import logging
from datetime import date, datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Codigo Python para la regla CN_AGUI_BASE
AGUI_BASE_CODE = (
    "# Suma de remuneraciones brutas (BASIC + ALW) del empleado en el ano\n"
    "year = payslip.date_to.year if payslip.date_to else 0\n"
    "Slip = payslip.env['hr.payslip'].sudo()\n"
    "Line = payslip.env['hr.payslip.line'].sudo()\n"
    "year_slips = Slip.search([\n"
    "    ('employee_id', '=', employee.id),\n"
    "    ('state', 'in', ['done', 'paid']),\n"
    "    ('date_from', '>=', '%d-01-01' % year),\n"
    "    ('date_to', '<=', '%d-12-31' % year),\n"
    "    ('id', '!=', payslip.id),\n"
    "])\n"
    "lines = Line.search([\n"
    "    ('slip_id', 'in', year_slips.ids),\n"
    "    ('category_id.code', 'in', ['BASIC', 'ALW']),\n"
    "])\n"
    "result = sum(lines.mapped('total'))\n"
)


def _build_aguinaldo_rules_def(env, struct):
    """Define las reglas de la estructura Aguinaldo Anual PY."""
    Cat = env['hr.salary.rule.category'].sudo()
    cat_basic = Cat.search([('code', '=', 'BASIC')], limit=1)
    cat_alw = Cat.search([('code', '=', 'ALW')], limit=1)
    cat_ded = Cat.search([('code', '=', 'DED')], limit=1)
    cat_net = Cat.search([('code', '=', 'NET')], limit=1)
    if not (cat_basic and cat_ded and cat_net):
        return []
    if not cat_alw:
        cat_alw = Cat.create({'name': 'Asignaciones', 'code': 'ALW'})
    return [
        {
            'name': 'Base Aguinaldo (Total Anual)',
            'code': 'CN_AGUI_BASE',
            'category_id': cat_basic.id,
            'sequence': 5,
            'condition_python': 'result = True',
            'amount_python_compute': AGUI_BASE_CODE,
            'appears_on_payslip': True,
        },
        {
            'name': 'Aguinaldo Bruto (Base / 12)',
            'code': 'CN_AGUI_BRUTO',
            'category_id': cat_alw.id,
            'sequence': 10,
            'condition_python': 'result = True',
            'amount_python_compute': (
                "base = categories['BASIC']\n"
                "result = base / 12.0\n"
            ),
            'appears_on_payslip': True,
        },
        {
            'name': 'IPS Trabajador 9% sobre Aguinaldo',
            'code': 'CN_AGUI_IPS_TRAB',
            'category_id': cat_ded.id,
            'sequence': 50,
            'condition_python': 'result = True',
            'amount_python_compute': (
                "alw = categories['ALW']\n"
                "result = - alw * 0.09\n"
            ),
            'appears_on_payslip': True,
        },
        {
            'name': 'Aguinaldo Neto a Pagar',
            'code': 'CN_AGUI_NETO',
            'category_id': cat_net.id,
            'sequence': 100,
            'condition_python': 'result = True',
            'amount_python_compute': (
                "alw = categories['ALW']\n"
                "ded = categories['DED']\n"
                "result = alw + ded\n"
            ),
            'appears_on_payslip': True,
        },
    ]


def _ensure_aguinaldo_structure(env):
    """Crea la estructura Aguinaldo Anual PY si no existe y aplica sus reglas."""
    Struct = env['hr.payroll.structure'].sudo()
    struct = Struct.search([('code', '=', 'CN_AGUI_PY')], limit=1)
    if not struct:
        # Buscar un parent type (estructura padre)
        parent_id = False
        if 'type_id' in Struct._fields:
            StructType = env['hr.payroll.structure.type'].sudo()
            stype = StructType.search([], limit=1)
            if stype:
                parent_id = stype.id
        vals = {
            'name': 'Aguinaldo Anual - Paraguay',
            'code': 'CN_AGUI_PY',
        }
        if parent_id and 'type_id' in Struct._fields:
            vals['type_id'] = parent_id
        try:
            struct = Struct.create(vals)
        except Exception as e:
            _logger.warning('No se pudo crear estructura Aguinaldo: %s', e)
            return None
    # Crear/actualizar reglas
    Rule = env['hr.salary.rule'].sudo()
    rules_def = _build_aguinaldo_rules_def(env, struct)
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
            continue
        vals = dict(rdef)
        vals.update({
            'struct_id': struct.id,
            'condition_select': 'python',
            'amount_select': 'code',
            'active': True,
        })
        Rule.create(vals)
    return struct


class HrAguinaldoWizard(models.TransientModel):
    _name = 'hr.aguinaldo.wizard'
    _description = 'Wizard Generar Aguinaldo Anual Paraguay'

    year = fields.Integer(string='Anio',
                          default=lambda s: fields.Date.today().year,
                          required=True)
    employee_ids = fields.Many2many('hr.employee',
                                    string='Empleados',
                                    domain=[('active', '=', True)])
    select_all = fields.Boolean(string='Todos los activos')
    summary = fields.Html(string='Resumen', readonly=True)

    def action_generate(self):
        self.ensure_one()
        # Asegurar estructura
        struct = _ensure_aguinaldo_structure(self.env)
        if not struct:
            raise UserError(_('No se pudo crear/encontrar la estructura '
                              'Aguinaldo Anual PY.'))
        # Empleados a procesar
        employees = self.employee_ids
        if self.select_all:
            employees = self.env['hr.employee'].search([('active', '=', True)])
        if not employees:
            raise UserError(_('Seleccione al menos un empleado o marque '
                              '"Todos los activos".'))
        # Periodo: 1-dic a 31-dic del ano indicado
        date_from = date(self.year, 12, 1)
        date_to = date(self.year, 12, 31)
        Payslip = self.env['hr.payslip'].sudo()
        created = 0
        skipped = 0
        for emp in employees:
            existing = Payslip.search([
                ('employee_id', '=', emp.id),
                ('struct_id', '=', struct.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to),
            ], limit=1)
            if existing:
                skipped += 1
                continue
            try:
                slip = Payslip.create({
                    'employee_id': emp.id,
                    'struct_id': struct.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'name': 'Aguinaldo %d - %s' % (self.year, emp.name or ''),
                })
                # Calcular automaticamente
                try:
                    slip.compute_sheet()
                except Exception:
                    pass
                created += 1
            except Exception as e:
                _logger.warning('No se pudo crear aguinaldo para %s: %s',
                                emp.name, e)
                skipped += 1
        # Devolver una accion que abre la lista de recibos creados.
        # No usar 'next' dentro de display_notification (causa error en cliente).
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recibos Aguinaldo %d (creados: %d, omitidos: %d)' % (
                self.year, created, skipped),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [
                ('struct_id', '=', struct.id),
                ('date_from', '=', fields.Date.to_string(date_from)),
            ],
            'target': 'current',
        }
