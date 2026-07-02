# -*- coding: utf-8 -*-
"""Linea de funcion en el Manual de Funciones de un puesto."""
from odoo import api, fields, models


class HrJobFunctionLine(models.Model):
    _name = 'hr.job.function.line'
    _description = 'Funcion del Puesto (Manual)'
    _order = 'job_id, sequence, id'

    job_id = fields.Many2one(
        'hr.job', string='Puesto', required=True, ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Orden', default=10)
    function_id = fields.Many2one(
        'hr.function.catalog', string='Funcion del Catalogo',
        ondelete='set null',
        help='Seleccione del catalogo para autocargar la descripcion. '
             'Puede dejarse vacio si la descripcion es totalmente custom.',
    )
    name = fields.Char(
        string='Funcion',
        help='Texto breve de la funcion (auto-llenado al elegir del '
             'catalogo).',
    )
    description = fields.Html(
        string='Descripcion',
        help='Descripcion detallada de la funcion. Se autocarga del '
             'catalogo y puede editarse libremente.',
    )

    @api.onchange('function_id')
    def _onchange_function_id(self):
        if self.function_id:
            if not self.name:
                self.name = self.function_id.name
            if not self.description:
                self.description = self.function_id.description
