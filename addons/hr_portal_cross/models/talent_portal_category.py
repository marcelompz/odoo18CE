# -*- coding: utf-8 -*-
"""Categoria/columna del portal Talento Humano."""
from odoo import fields, models


class TalentPortalCategory(models.Model):
    _name = 'talent.portal.category'
    _description = 'Categoria del Portal Talento Humano'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, translate=True)
    sequence = fields.Integer(default=10)
    icon_class = fields.Char(string='Icono Font Awesome', default='fa-folder')
    color = fields.Char(
        string='Color de cabecera (hex)', default='#667eea',
        help='Color de fondo de la cabecera de la columna. Ej: #667eea',
    )
    description = fields.Char(string='Descripcion')
    active = fields.Boolean(default=True)
    tile_count = fields.Integer(
        string='Tiles', compute='_compute_tile_count',
    )

    def _compute_tile_count(self):
        Tile = self.env['talent.portal.tile']
        for cat in self:
            cat.tile_count = Tile.search_count([('category_id', '=', cat.id)])
