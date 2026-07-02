# -*- coding: utf-8 -*-
"""
Created on 2025-06-14 17:54:16

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductMolding(models.Model):
    _name = 'product.molding'
    _description = 'Moldería de productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_molding_id', string='Productos relacionados')
    code = fields.Char(
        string='Código')
    date = fields.Date(
        string='Fecha de creación de la moldería')
    type = fields.Selection(
        string='Tipo', selection=[('base', 'Base'),('transformed', 'Transformada'), ('industrialized', 'Industrializada')], default='base')
    moldebacista_id = fields.Many2one(
        'hr.employee', string='Moldebacista')
    creative_id = fields.Many2one(
        'hr.employee', string='Creativa')
    mold_base_ids = fields.Many2many(
        'product.molding.size', 'product_molding_mold_base_rel', 'molding_id', 'mold_size_id', string='Tamaño base del molde',  ondelete='restrict')
    size_system = fields.Selection(
        string='Sistema de tallaje usado', selection=[('latin_american', 'Latinoamericano'), ('european', 'Europeo'), ('american', 'Americano')], default='latin_american')
    software_used_id = fields.Many2one(
        'product.molding.software', string='Software utilizado', ondelete='restrict')
    scaling_available_ids = fields.Many2many(
        'product.molding.size', 'product_molding_scaling_rel', 'molding_id', 'scaling_size_id', string='Escalado disponible',  ondelete='restrict')
    parts_ids = fields.Many2many(
        'product.molding.parts', string='Piezas del molde', ondelete='restrict')
    note = fields.Text(
        string='Observaciones')
    product_type_fabric_id = fields.Many2one(
        'product.type.fabric', string='Tipo de tela principal', ondelete='restrict')
    product_type_fabric_ids = fields.Many2many(
        'product.type.fabric', 'product_molding_type_fabric_rel', 'molding_id', 'type_fabric_id', string='Tipos de tela secundarias', ondelete='restrict')
    consumption = fields.Float(
        string='Consumo', help='Consumo estimado de tela por talle', digits=(16, 2), default=0.0)
    elasticity_product_type_fabric_ids = fields.Many2many(
        'product.type.fabric', 'product_molding_elasticity_fabric_rel', 'molding_id', 'elasticity_fabric_id', string='Elasticidad', ondelete='restrict')
    weight_fabric = fields.Float(
        string='Gramaje del tejido', digits=(16, 2), default=0.0)
    type_of_fabric = fields.Text(
        string='Tipo de tejido')
    document_attachment = fields.Html(
        string='Descripción')
    type_thread_ids = fields.Many2many(
        'product.type.thread', 'product_molding_type_thread_rel', 'molding_id', 'type_thread_id', string='Tipos de hilo', ondelete='restrict')
    molding_label_ids = fields.Many2many(
        'product.molding.label', 'product_molding_label_rel', 'molding_id', 'label_id', string='Etiquetas de moldería', ondelete='restrict')
    molding_prints = fields.Boolean(
        string='Estampado')
    embroidery = fields.Boolean(
        string='Bordados')
    sublimation = fields.Boolean(
        string='Sublimación')
    molding_fly = fields.Boolean(
        string='Cierre')
    molding_buttons = fields.Boolean(
        string='Botones')
    molding_elastic = fields.Boolean(
        string='Elasticos')
    molding_bias = fields.Boolean(
        string='Bies')
    composition_label = fields.Boolean(
        string='Etiqueta de composición')
    size_label = fields.Boolean(
        string='Etiqueta de tamaño')
    brand_label = fields.Boolean(
        string='Etiqueta de marca')
    other_avios = fields.Text(
        string='Otros avíos')


class ProductMoldingSize(models.Model):
    _name = 'product.molding.size'
    _description = 'Tallas de moldería'

    name = fields.Char(
        string='Nombre')


class ProductMoldingSoftware(models.Model):
    _name = 'product.molding.software'
    _description = 'Software de moldería'

    name = fields.Char(
        string='Nombre')


class ProductMoldingSoftwareParts(models.Model):
    _name = 'product.molding.parts'
    _description = 'Piezas de moldería'

    name = fields.Char(
        string='Nombre')


class ProductTypeFabric(models.Model):
    _name = 'product.type.fabric'
    _description = 'Tipo de tela'

    name = fields.Char(
        string='Nombre')


class ProductTypeThread(models.Model):
    _name = 'product.type.thread'
    _description = 'Tipo de hilo'

    name = fields.Char(
        string='Nombre')


class ProductMoldingLabel(models.Model):
    _name = 'product.molding.label'
    _description = 'Etiqueta de moldería'

    name = fields.Char(
        string='Nombre')
