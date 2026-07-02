# -*- coding: utf-8 -*-
from odoo import fields, models


class HrBonificationCategory(models.Model):
    _name = 'hr.bonification.category'
    _description = 'Categoría de Bonificaciones'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True, help='Código único para identificar la categoría')
    sequence = fields.Integer(string='Secuencia', default=10, help='Orden de visualización')
    description = fields.Text(string='Descripción')
    bonification_ids = fields.One2many(
        'hr.bonification',
        'category_id',
        string='Bonificaciones',
        help='Bonificaciones asociadas a esta categoría'
    )
    active = fields.Boolean(string='Activo', default=True)

