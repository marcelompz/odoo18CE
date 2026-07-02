# -*- coding: utf-8 -*-
"""Extension de hr.contract.type para marcar tipos de contrato como
jornalero (Paraguay).
"""
from odoo import _, fields, models


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    cn_is_jornalero = fields.Boolean(
        string='Pago tipo Jornalero (Paraguay)',
        default=False,
        help='Si esta marcado, los empleados con este tipo de contrato se '
             'pagan como jornalero (salario diario = wage/26, solo dias '
             'trabajados). Si no esta marcado, se pagan como mensualizado '
             '(salario diario = wage/30, todos los dias del mes incluidos).',
    )
