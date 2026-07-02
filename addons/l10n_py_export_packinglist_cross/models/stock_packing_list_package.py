# -*- coding: utf-8 -*-
import math

from odoo import api, fields, models


class StockPackingListPackage(models.Model):
    """Bulto fisico (BOX / CAJA) dentro de un Packing List.

    Un bulto puede contener una o varias lineas (productos distintos),
    y tiene su propio peso vacio, dimensiones y embalaje.
    """
    _name = 'stock.packing.list.package'
    _description = 'Bulto / Caja del Packing List'
    _order = 'packing_list_id, sequence, id'

    packing_list_id = fields.Many2one(
        comodel_name='stock.packing.list', string='Packing List',
        required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(
        string='Nro BOX', default=10, index=True,
        help='Numero secuencial del bulto dentro del Packing List.',
    )
    name = fields.Char(
        string='Nombre BOX',
        compute='_compute_name', store=True, readonly=False,
        help='Identificador del bulto. Por defecto se calcula automaticamente.',
    )

    # Embalaje y peso vacio
    packaging_id = fields.Many2one(
        comodel_name='product.packaging',
        string='Embalaje',
        help='Embalaje (referencia opcional al modulo nativo). Al seleccionarlo, '
             'se sugiere su peso vacio.',
    )
    empty_weight = fields.Float(
        string='Peso Vacio (kg)', digits=(16, 3),
        help='Peso del bulto vacio (sin contenido). Se suma al peso neto para '
             'obtener el peso bruto.',
    )
    dimensions = fields.Char(
        string='Dimensiones',
        help='Ej: 80x60x40 cm (Largo x Ancho x Alto).',
    )
    notes = fields.Char(string='Observaciones del bulto')

    # Lineas
    line_ids = fields.One2many(
        comodel_name='stock.packing.list.line',
        inverse_name='package_id',
        string='Lineas',
        copy=True,
    )
    line_count = fields.Integer(
        string='Cant. Lineas', compute='_compute_line_count', store=True,
    )

    # Pesos y volumen computados
    net_weight = fields.Float(
        string='Peso Neto (kg)', digits=(16, 3),
        compute='_compute_weights', store=True,
        help='Suma del peso neto de todas las lineas del bulto.',
    )
    gross_weight = fields.Float(
        string='Peso Bruto (kg)', digits=(16, 3),
        compute='_compute_weights', store=True,
        help='Peso Neto + Peso Vacio del bulto.',
    )
    volume = fields.Float(
        string='Volumen (m3)', digits=(16, 4),
        compute='_compute_weights', store=True,
    )
    total_quantity = fields.Float(
        string='Cant. Total Productos', digits='Product Unit of Measure',
        compute='_compute_weights', store=True,
    )

    company_id = fields.Many2one(
        related='packing_list_id.company_id', store=True,
    )
    currency_id = fields.Many2one(
        related='packing_list_id.currency_id', store=True,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('sequence', 'packing_list_id')
    def _compute_name(self):
        for rec in self:
            if not rec.name:
                rec.name = 'BOX %s' % (rec.sequence or '?')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids', 'line_ids.net_weight', 'line_ids.volume',
                 'line_ids.quantity', 'empty_weight')
    def _compute_weights(self):
        for rec in self:
            rec.net_weight = sum(rec.line_ids.mapped('net_weight'))
            rec.gross_weight = rec.net_weight + (rec.empty_weight or 0.0)
            rec.volume = sum(rec.line_ids.mapped('volume'))
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))

    # ------------------------------------------------------------------
    # Onchanges
    # ------------------------------------------------------------------
    @api.onchange('packaging_id')
    def _onchange_packaging_id(self):
        """Al elegir un embalaje, sugerir peso vacio si no esta cargado."""
        if self.packaging_id and not self.empty_weight:
            pkg = self.packaging_id
            empty = 0.0
            if 'package_empty_weight' in pkg._fields and pkg.package_empty_weight:
                empty = pkg.package_empty_weight
            elif 'package_type_id' in pkg._fields and pkg.package_type_id \
                    and 'base_weight' in pkg.package_type_id._fields:
                empty = pkg.package_type_id.base_weight or 0.0
            if empty:
                self.empty_weight = empty
