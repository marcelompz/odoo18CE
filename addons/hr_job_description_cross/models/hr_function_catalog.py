# -*- coding: utf-8 -*-
"""Catalogo de funciones reutilizables para Manual de Funciones."""
from odoo import fields, models


class HrFunctionCatalog(models.Model):
    _name = 'hr.function.catalog'
    _description = 'Catalogo de Funcion del Manual de Puesto'
    _order = 'sequence, name'

    name = fields.Char(string='Funcion', required=True, translate=True)
    sequence = fields.Integer(string='Orden', default=10)
    category = fields.Selection([
        ('operational', 'Operacional'),
        ('quality', 'Control de Calidad'),
        ('safety', 'Seguridad'),
        ('admin', 'Administrativa'),
        ('management', 'Gestion'),
        ('communication', 'Comunicacion'),
        ('other', 'Otra'),
    ], string='Categoria', default='operational')
    description = fields.Html(
        string='Descripcion detallada',
        help='Descripcion estandar de la funcion. Se autocarga al '
             'seleccionar en la linea del puesto, y luego puede editarse '
             'manualmente.',
    )
    active = fields.Boolean(default=True)
