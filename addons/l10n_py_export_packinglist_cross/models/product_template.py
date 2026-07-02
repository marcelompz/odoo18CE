# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ncm = fields.Char(
        string='NCM',
        help='Nomenclatura Comun del Mercosur. Codigo arancelario utilizado '
             'en Paraguay, Argentina, Brasil y Uruguay para clasificacion aduanera.',
    )
    # Campo legacy mantenido por compatibilidad con vistas / modulos heredados.
    hs_code = fields.Char(
        string='HS Code (legacy)',
        compute='_compute_hs_code',
        inverse='_inverse_hs_code',
        store=True,
        help='Campo legacy. Use el campo NCM. Se mantiene sincronizado con NCM.',
    )
    # Embalaje por defecto -> usa el modelo nativo product.packaging (Odoo "Embalaje")
    default_packaging_id = fields.Many2one(
        comodel_name='product.packaging',
        string='Tipo de Bulto por Defecto',
        domain="[('product_id.product_tmpl_id', '=', id)]",
        help='Embalaje (BAG, CTN, DRM, PLT, BOX, etc.) usado por defecto al generar '
             'el Packing List. Se toma del modulo nativo de Embalajes de Odoo.',
    )
    # ----------------------------------------------------------------------
    # Campos LEGACY mantenidos por compatibilidad con vistas o registros previos.
    # NO se usan en la logica actual; se conservan para evitar romper xpaths
    # heredados u otras vistas que aun los referencien.
    # ----------------------------------------------------------------------
    default_package_type = fields.Char(
        string='Tipo de Bulto (legacy)',
        compute='_compute_default_package_type',
        inverse='_inverse_default_package_type',
        store=True,
        help='[LEGACY] Use "Tipo de Bulto por Defecto" (default_packaging_id). '
             'Este campo se sincroniza con el nombre del embalaje.',
    )
    default_net_weight = fields.Float(
        string='Peso Neto por Defecto (legacy, kg)', digits=(16, 3),
        compute='_compute_default_weight',
        inverse='_inverse_default_net_weight',
        store=True,
        help='[LEGACY] Use el campo nativo "Peso" del producto.',
    )
    default_gross_weight = fields.Float(
        string='Peso Bruto por Defecto (legacy, kg)', digits=(16, 3),
        compute='_compute_default_weight',
        inverse='_inverse_default_gross_weight',
        store=True,
        help='[LEGACY] Use el campo nativo "Peso" del producto.',
    )

    @api.depends('ncm')
    def _compute_hs_code(self):
        for rec in self:
            rec.hs_code = rec.ncm

    def _inverse_hs_code(self):
        for rec in self:
            if rec.hs_code != rec.ncm:
                rec.ncm = rec.hs_code

    @api.depends('default_packaging_id', 'default_packaging_id.name')
    def _compute_default_package_type(self):
        for rec in self:
            rec.default_package_type = rec.default_packaging_id.name if rec.default_packaging_id else False

    def _inverse_default_package_type(self):
        # Solo guarda el texto; no crea ni busca embalaje automaticamente.
        # El usuario debe seleccionar el embalaje en default_packaging_id.
        return

    @api.depends('weight')
    def _compute_default_weight(self):
        for rec in self:
            rec.default_net_weight = rec.weight or 0.0
            rec.default_gross_weight = rec.weight or 0.0

    def _inverse_default_net_weight(self):
        for rec in self:
            if rec.default_net_weight and not rec.weight:
                rec.weight = rec.default_net_weight

    def _inverse_default_gross_weight(self):
        for rec in self:
            if rec.default_gross_weight and not rec.weight:
                rec.weight = rec.default_gross_weight


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ncm = fields.Char(related='product_tmpl_id.ncm', store=True, readonly=False)
    hs_code = fields.Char(related='product_tmpl_id.hs_code', store=True, readonly=False)
    default_packaging_id = fields.Many2one(
        related='product_tmpl_id.default_packaging_id',
        store=True, readonly=False,
    )
    default_package_type = fields.Char(
        related='product_tmpl_id.default_package_type',
        store=True, readonly=False,
    )
    default_net_weight = fields.Float(
        related='product_tmpl_id.default_net_weight',
        store=True, readonly=False,
    )
    default_gross_weight = fields.Float(
        related='product_tmpl_id.default_gross_weight',
        store=True, readonly=False,
    )
