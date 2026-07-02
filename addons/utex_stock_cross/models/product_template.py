# -*- coding: utf-8 -*-
"""
Created on 2025-05-21 09:08:27

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    product_brand_id = fields.Many2one(
        'product.brand', string='Marca del producto', ondelete='restrict')
    product_collection_id = fields.Many2one(
        'product.collection', string='Colección del producto', ondelete='restrict')
    product_initial_id = fields.Many2one(
        'product.initial', string='Producto inicial', ondelete='restrict')
    product_model_id = fields.Many2one(
        'product.model', string='Modelo del producto', ondelete='restrict')
    product_combination_fabrics_id = fields.Many2many(
        'product.combination.fabrics', string='Combinación de telas', ondelete='restrict')
    product_molding_id = fields.Many2one(
        'product.molding', string='Moldería del producto', ondelete='restrict')
    product_gender_id = fields.Many2one(
        'product.gender', string='Género del producto', ondelete='restrict')
    product_type_use_id = fields.Many2one(
        'product.type.use', string='Tipo de uso', ondelete='restrict')
    product_class = fields.Selection(
        string='Clase de producto', selection=[('raw_material', 'Materia prima'),('merchandise', 'Mercadería')], default='merchandise')
    product_attribute_attribute_ids = fields.Many2many(
        'product.attribute.attribute', string='Atributos del producto', ondelete='restrict')
    product_online_technology_ids = fields.Many2many(
        'product.online.technology', string='Tecnología en línea del producto', ondelete='restrict')
    product_composition = fields.Char(
        string='Composición del producto')
    product_width = fields.Char(
        string='Ancho')
    product_grammar = fields.Char(
        string='Gramatura')
    product_performance = fields.Char(
        string='Rendimiento')
    suggested_alert = fields.Boolean(
        string='Alerta de sugerencia', compute='_compute_suggested_alert')
    revenue = fields.Monetary(
        string='Ganancia', currency_field='currency_id', compute='_compute_revenue')
    margin_on_sale = fields.Float(
        string='% de Margen s/venta', compute='_compute_revenue', digits=(16, 2))
    margin_over_cost = fields.Float(
        string='% de Margen s/costo', compute='_compute_revenue', digits=(16, 2))
    product_design_id = fields.Many2one(
        'product.design', string='Diseño')
    product_color_id = fields.Many2one(
        'product.attribute.value', string='Color del producto', ondelete='restrict')

    @api.depends('standard_price', 'list_price')
    def _compute_revenue(self):
        for record in self:
            list_price = record.list_price or 0.0
            cost_price = record.standard_price or 0.0
            revenue = list_price - cost_price

            record.revenue = revenue
            record.margin_on_sale = (revenue / list_price) if list_price else 0.0
            record.margin_over_cost = (revenue / cost_price) if cost_price else 0.0

    @api.depends('suggested_value', 'margin_gain', 'coefficient_value')
    def _compute_suggested_alert(self):
        for record in self:
            record.suggested_alert = self.suggested_value > self.coefficient_value
    
    def recalculate_coefficient_from_margin(self):
        self.suggested_value = self.standard_price + (self.standard_price * self.margin_gain)

        if self.suggested_value < self.coefficient_value:
            self.list_price = self.coefficient_value

    def _get_dynamic_field_value(self, record, field_name):
        """
        Helper para extraer el valor legible según el tipo de campo.
        """
        # 1. Obtenemos el valor "crudo" y la definición del campo
        val = record[field_name]
        field_type = record._fields[field_name].type

        if not val:
            return ""

        # 2. Lógica por tipo de campo
        if field_type == 'many2one':
            # Devolvemos el nombre del registro relacionado
            return val.name or ""
            
        elif field_type in ['many2many', 'one2many']:
            # Devolvemos una lista separada por comas (Ej: "Etiqueta1, Etiqueta2")
            return ", ".join(val.mapped('name'))
            
        elif field_type == 'selection':
            # Obtenemos la etiqueta (Label) en lugar de la clave interna
            # Ejemplo: 'draft' -> 'Borrador'
            return dict(record._fields[field_name]._description_selection(self.env)).get(val) or str(val)
            
        elif field_type == 'boolean':
            # Opcional: devolver el nombre del campo si es True
            return record._fields[field_name].string if val else ""
            
        else:
            # Char, Integer, Float, Text, etc.
            return str(val)

    # Dependemos de 'name' como base. Odoo recalculará esto al leer el registro.
    @api.depends('name') 
    def _compute_display_name(self):
        # 1. Obtenemos la configuración UNA sola vez (fuera del bucle for para rendimiento)
        # Usamos sudo() por si el usuario no tiene permiso de leer la configuración
        name_sequences = self.env['product.name.sequence'].sudo().search([], order='sequence asc')
        
        # Si no hay configuración, usamos el comportamiento estándar
        if not name_sequences:
            return super()._compute_display_name()

        # Extraemos solo los nombres técnicos de los campos (ej: ['default_code', 'name', 'categ_id'])
        field_names = name_sequences.mapped('fields_id.name')

        for record in self:
            parts = []
            
            # 2. Iteramos sobre los campos configurados
            for f_name in field_names:
                # Verificamos que el campo exista en el modelo (seguridad ante borrados)
                if f_name in record._fields:
                    try:
                        clean_val = self._get_dynamic_field_value(record, f_name)
                        if clean_val:
                            parts.append(clean_val)
                    except Exception as e:
                        # Si falla un campo, no rompemos todo el sistema, seguimos con el siguiente
                        continue

            # 3. Armamos el nombre final
            if parts:
                record.display_name = " ".join(parts)

            else:
                # Fallback por si los campos configurados están vacíos
                record.display_name = record.name or ""

            record._onchange_display_name()

    @api.onchange('display_name')
    def _onchange_display_name(self):
        for line in self:
            line.name = line.display_name
    
    def action_mass_update_display_name(self):
        """
        Fuerza el recálculo del display_name para los registros seleccionados.
        """
        self._compute_display_name()
        self._onchange_display_name()
        return True

    @api.onchange('product_initial_id')
    def _onchange_product_initial_id(self):
        self.name = self.product_initial_id.name
    
    @api.model_create_multi
    def create(self, vals_list):
        # Si el usuario NO es administrador de inventario, bloqueamos la creación
        if self.env.user.has_group('utex_stock_cross.group_forcing_not_to_create_products_cross'):
            raise AccessError(_("No tienes permisos para crear productos. Contacta con tu supervisor."))

        for vals in vals_list:
            if 'categ_id' in vals and not vals.get('default_code'):
                category = self.env['product.category'].browse(vals['categ_id'])
                
                child_prefix = self._generate_category_prefix(category.name) or category.name[:3].upper()

                # Obtener prefijo de la categoría padre
                parent_prefix = ''
                if category.parent_id:
                    parent_prefix = self._generate_category_prefix(category.parent_id.name) or category.parent_id.name[:3].upper()
                
                # Generar secuencia (ej. una secuencia global o una por categoría)
                # Podrías tener una secuencia por cada combinación de prefijos si lo necesitas
                sequence_code = 'product.product.cross'
                next_number = self.env['ir.sequence'].next_by_code(sequence_code) or '0001'

                # Construir la referencia interna
                if parent_prefix:
                    vals['default_code'] = f"{child_prefix}/{parent_prefix}{next_number}"
                else:
                    vals['default_code'] = f"{child_prefix}/{next_number}"

        return super().create(vals_list)

    # Método auxiliar para generar un prefijo (ejemplo básico)
    def _generate_category_prefix(self, category_name):
        words = category_name.split(' ')
        prefix_parts = []
        for word in words:
            if word and word.upper() not in ['DE', 'LA', 'EL', 'LOS', 'LAS', 'Y', 'O']: # Ignorar palabras comunes
                prefix_parts.append(word[:3].upper()) # Tomar las primeras 3 letras en mayúsculas
        return '-'.join(prefix_parts) if prefix_parts else category_name[:3].upper()

    @api.onchange('product_initial_id', 'product_model_id')
    def _onchange_generate_default_code(self):
        """
        Genera automáticamente la Referencia Interna (default_code)
        basada en Producto Inicial + Modelo.
        """
        for record in self:
            # Obtenemos los códigos o cadenas vacías si no hay selección
            code_initial = record.product_initial_id.code or ''
            code_model = record.product_model_id.code or ''
            
            # Filtramos para no tener guiones sueltos si falta uno de los dos
            parts = [c for c in [code_initial, code_model] if c]
            
            # Unimos con un guion (o puedes poner "".join(parts) si lo quieres pegado)
            new_code = "".join(parts)
            
            # Asignamos al default_code (Referencia Interna)
            if new_code:
                record.default_code = new_code

    # def action_force_recompute_display_name(self):
    #     """
    #     Esta acción de servidor recalcula el display_name para los productos seleccionados
    #     y muestra una notificación al usuario.
    #     """
    #     self._compute_display_name()
    #     product_names = self.mapped('display_name')
    #     notification_message = _(
    #         "Se ha recalculado el display_name para %d productos.",
    #         len(product_names)
    #     )

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'type': 'success',
    #             'title': _("Recálculo Exitoso"),
    #             'message': notification_message,
    #             'sticky': False,
    #         }
    #     }


class ProductInitial(models.Model):
    _name = 'product.initial'
    _description = 'Producto Inicial'

    name = fields.Char(
        string='Nombre')
    code = fields.Char(
        string='Código')
    product_template_ids = fields.One2many(
        'product.template', 'product_initial_id', string='Productos relacionados')


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Marca de productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_brand_id', string='Productos relacionados')
    

class ProductCollection(models.Model):
    _name = 'product.collection'
    _description = 'Colección de productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_collection_id', string='Productos relacionados')


class ProductModel(models.Model):
    _name = 'product.model'
    _description = 'Modelo del producto'

    name = fields.Char(
        string='Nombre')
    code = fields.Char(
        string='Código')
    product_template_ids = fields.One2many(
        'product.template', 'product_model_id', string='Productos relacionados')


class ProductCombinationFabrics(models.Model):
    _name = 'product.combination.fabrics'
    _description = 'Combinación de telas'

    name = fields.Char(
        string='Nombre')
    code = fields.Char(
        string='Código')
    product_template_ids = fields.One2many(
        'product.template', 'product_model_id', string='Productos relacionados')


class ProductGender(models.Model):
    _name = 'product.gender'
    _description = 'Moldería de productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_gender_id', string='Productos relacionados')


class ProductTypeUse(models.Model):
    _name = 'product.type.use'
    _description = 'Tipo de uso del productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_type_use_id', string='Productos relacionados')


class ProductTemplateTemplate(models.Model):
    _name = 'product.attribute.attribute'
    _description = 'Atributo del productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_type_use_id', string='Productos relacionados')


class ProductOnlineTechnology(models.Model):
    _name = 'product.online.technology'
    _description = 'Tecnología en línea del productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_type_use_id', string='Productos relacionados')


class ProductDesign(models.Model):
    _name = 'product.design'
    _description = 'Diseño del productos'

    name = fields.Char(
        string='Nombre')
    product_template_ids = fields.One2many(
        'product.template', 'product_type_use_id', string='Productos relacionados')
