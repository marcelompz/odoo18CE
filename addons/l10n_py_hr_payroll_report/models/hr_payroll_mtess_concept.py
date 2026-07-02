# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayrollMtessConcept(models.Model):
    _name = 'hr.payroll.mtess.concept'
    _description = 'Conceptos MTESS - Planilla Laboral Mensual'
    _order = 'sequence, id'

    grupo = fields.Selection(
        [
            ('SALARIO', 'SALARIO'),
            ('HORAS_EXTRAS', 'HORAS EXTRAS'),
            ('BENEFICIOS', 'BENEFICIOS SOCIALES'),
            ('TOTAL', 'TOTAL GENERAL'),
        ],
        string='Grupo',
        default='SALARIO',
        required=True,
    )
    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    value_type = fields.Selection(
        [
            ('salary_rule', 'Reglas salariales'),
            ('fixed', 'Valor fijo'),
        ],
        string='Tipo de valor',
        default='salary_rule',
        required=True,
    )
    code_list = fields.Char(
        string='Codigos de Regla',
        help="Codigos de reglas salariales separados por coma. Ej: BASIC, PY_ADICIONALES",
    )
    exclude_code_list = fields.Char(
        string='Excluir Codigos',
        help="Codigos a restar del total (separados por coma).",
    )
    fixed_code = fields.Selection(
        [
            ('FORMA_PAGO', 'Forma de Pago'),
            ('IMPORTE_UNITARIO', 'Importe Unitario'),
            ('DIAS_TRAB', 'Dias de trabajo'),
            ('HORAS_TRAB', 'Horas trabajadas'),
            ('IMPORTE', 'Importe'),
            ('HE_50', '50%'),
            ('HE_100', '100%'),
            ('HE_IMPORTE', 'IMPORTE Horas Extras'),
            ('TOTAL_GENERAL', 'Incluyendo horas Extras y Beneficios Sociales'),
        ],
        string='Valor fijo',
    )
    include_in_total = fields.Boolean(
        string='Incluir en total',
        default=True,
        help="Suma este concepto en el total general.",
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

    display_code = fields.Char(string='Codigo', compute='_compute_display_fields')
    display_calc_type = fields.Char(string='Tipo de calculo', compute='_compute_display_fields')

    def _compute_display_fields(self):
        for rec in self:
            if rec.value_type == 'fixed':
                rec.display_code = rec.fixed_code or ''
                rec.display_calc_type = 'Fijo'
            else:
                rec.display_code = rec.code_list or ''
                rec.display_calc_type = dict(self._fields['compute_mode'].selection).get(rec.compute_mode, '')
