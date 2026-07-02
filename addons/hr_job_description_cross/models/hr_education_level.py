# -*- coding: utf-8 -*-
"""Catalogo de niveles de formacion academica para usar como
requisitos minimos en hr.job (Manual de Funciones)."""
from odoo import fields, models


class HrEducationLevel(models.Model):
    _name = 'hr.education.level'
    _description = 'Nivel de Formacion Academica'
    _order = 'sequence, name'

    name = fields.Char(string='Nivel', required=True, translate=True)
    sequence = fields.Integer(string='Orden', default=10)
    description = fields.Text(string='Descripcion')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color')
