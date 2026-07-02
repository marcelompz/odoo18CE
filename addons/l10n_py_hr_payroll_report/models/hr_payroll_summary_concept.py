# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayrollSummaryConcept(models.Model):
    _name = 'hr.payroll.summary.concept'
    _description = 'Conceptos de Planilla de Salarios'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    code_list = fields.Char(
        string='Codigos de Regla',
        help="Codigos de reglas salariales separados por coma. Ej: BASIC, PY_TOTAL_BRUTO",
    )
    compute_mode = fields.Selection(
        [
            ('sum', 'Sumar todos'),
            ('first_nonzero', 'Primer valor no cero'),
        ],
        string='Modo de calculo',
        default='sum',
        required=True,
    )
    use_abs = fields.Boolean(string='Mostrar absoluto', default=False)
    active = fields.Boolean(string='Activo', default=True)
