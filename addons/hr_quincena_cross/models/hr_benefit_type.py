# -*- coding: utf-8 -*-
"""Tipos configurables de Beneficio para empleados.

Permite a RRHH definir libremente los tipos disponibles (Prestamo, Uniforme,
Prestamo de Emergencia, Beneficio sin devolucion, etc.) en lugar de tener
un Selection rigido en el modelo hr.loan.
"""
from odoo import _, api, fields, models


class HrBenefitType(models.Model):
    _name = 'hr.benefit.type'
    _description = 'Tipo de Beneficio para Empleado'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Codigo', required=True, copy=False,
        help='Codigo unico interno (ej. PRESTAMO, UNIFORME, EMERGENCIA).')
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    description = fields.Text(string='Descripcion')

    is_fractional_default = fields.Boolean(
        string='Se fracciona por defecto', default=True,
        help='Si esta activo, al elegir este tipo en un Beneficio nuevo se '
             'marcara automaticamente "Se fracciona en cuotas". El usuario '
             'puede cambiarlo manualmente para cada caso.',
    )
    requires_seniority = fields.Boolean(
        string='Requiere antiguedad minima', default=False,
        help='Si esta activo, al aprobar un Beneficio de este tipo el sistema '
             'valida que el empleado tenga la antiguedad minima configurada '
             'en la empresa (cn_antiguedad_minima_prestamo_dias).',
    )
    default_installments = fields.Integer(
        string='Cuotas por defecto', default=6,
        help='Cantidad de cuotas sugerida al crear un Beneficio de este tipo.',
    )
    color = fields.Integer(string='Color', default=0)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El codigo del tipo de beneficio debe ser unico.'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} [{rec.code}]" if rec.code else rec.name
