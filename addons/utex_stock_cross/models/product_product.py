# -*- coding: utf-8 -*-
"""
Created on 2025-05-22 14:05:45

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    product_color_id = fields.Many2one(
        related='product_tmpl_id.product_color_id', store=True, readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobreescribe el método create para generar un código de producto personalizado.
        El formato es: PREFIJO_CATEGORIA_PADRE / PREFIJO_CATEGORIA + NUMERO_SECUENCIA
        Ejemplo: EST-DEP-FUT/REM0001
        """
        # Si el usuario NO es administrador de inventario, bloqueamos la creación
        if self.env.user.has_group('utex_stock_cross.group_forcing_not_to_create_products_cross'):
            raise AccessError(_("No tienes permisos para crear productos. Contacta con tu supervisor."))

        for vals in vals_list:
            # Solo generamos un código personalizado si 'default_code' no está proporcionado
            # o si está vacío en los valores de creación.
            if 'default_code' not in vals or not vals.get('default_code'):
                generated_code_parts = []
                
                # Obtener la categoría del producto (categ_id)
                categ_id = vals.get('categ_id')
                category = False
                if categ_id:
                    category = self.env['product.category'].browse(categ_id)

                if category and category.exists():
                    # 1. Prefijo de la Categoría Padre
                    parent_prefixes = []
                    if category.parent_path:
                        # parent_path es una cadena como '1/5/10/'
                        # Dividimos por '/' y filtramos IDs vacíos o el ID de la categoría actual
                        parent_ids = [
                            int(x) for x in category.parent_path.split('/')
                            if x and int(x) != category.id
                        ]
                        
                        # Obtenemos los registros de las categorías padre en orden
                        # (ordenar por ID suele mantener el orden de la jerarquía)
                        parents = self.env['product.category'].browse(parent_ids).sorted(key=lambda c: c.id)

                        for parent in parents:
                            # Dividir el nombre de la categoría padre en palabras
                            # y tomar las tres primeras letras de cada palabra en mayúsculas
                            words = parent.name.split()
                            word_initials = [word[:3].upper() for word in words if word]
                            if word_initials:
                                parent_prefixes.append("-".join(word_initials))

                    parent_code_part = "-".join(parent_prefixes) if parent_prefixes else ""

                    # 2. Prefijo de la Categoría Asignada
                    category_code_part = category.name[:3].upper() if category.name else ""

                    # 3. Número de Secuencia
                    # Usamos la secuencia 'product.product.cross' que definiste en XML
                    sequence_number = self.env['ir.sequence'].next_by_code('product.product.cross') or ''

                    # Construir el código final según el formato deseado:
                    # EST-DEP-FUT/REM0001
                    final_code_segments = []

                    if parent_code_part:
                        final_code_segments.append(parent_code_part)
                    
                    # Si hay una parte de categoría padre Y un prefijo de categoría,
                    # añadimos el separador '/'
                    if parent_code_part and category_code_part:
                        final_code_segments.append("/")
                    
                    if category_code_part:
                        final_code_segments.append(category_code_part)

                    # El número de secuencia se añade directamente sin separador adicional
                    if sequence_number:
                        final_code_segments.append(sequence_number)
                    
                    vals['default_code'] = "".join(final_code_segments)
                else:
                    # Fallback si no se puede determinar la categoría o no hay información
                    # O si la secuencia no genera un número (lo cual es raro si está bien configurada)
                    vals['default_code'] = self.env['ir.sequence'].next_by_code('product.product.cross') or _('NEW')

        # Llama al método create original del modelo base de Odoo
        return super().create(vals_list)

    @api.depends(
        'name',
        'default_code',
        'product_tmpl_id.company_id.configure_product_display_name',
        # Añade aquí los campos de los que dependas, accediendo vía product_tmpl_id si son del template
        'product_tmpl_id.product_brand_id.name', 
        'product_tmpl_id.product_collection_id.name',
        # etc...
    )
    # v18: context='display_name' ayuda a invalidar caché correctamente si cambia el contexto
    def _compute_display_name(self):
        # 1. Comprobación rápida de configuración (evitamos lógica si no aplica)
        # Usamos self.env.company con cuidado, idealmente deberíamos mirar la compañía del producto
        if not self.env.company.configure_product_display_name:
            return super()._compute_display_name()

        # 2. Optimización: Buscar la secuencia FUERA del bucle
        # Solo lo hacemos una vez para todo el lote de productos
        field_sequences = self.env['product.name.sequence'].search([], order='sequence asc')
        
        if not field_sequences:
            return super()._compute_display_name()

        # Pre-cargar los nombres de los campos para no acceder a bd dentro del bucle
        fields_to_read = [f.fields_id.name for f in field_sequences if f.fields_id.name]

        for product in self:
            parts = []
            
            # Iteramos sobre la configuración, no sobre los campos del modelo directamente
            for seq_rec in field_sequences:
                field_name = seq_rec.fields_id.name
                
                # En product.product, muchos campos del template son accesibles directamente,
                # pero si el campo es exclusivo del template y no delegate, usa product.product_tmpl_id
                if not hasattr(product, field_name):
                    continue

                field_value = product[field_name]
                
                # Si no tiene valor, saltamos
                if not field_value:
                    continue

                # Obtenemos metadata del campo
                field_meta = product._fields[field_name]

                if field_meta.type == 'many2one':
                    if field_meta.comodel_name == 'product.attribute.value':
                        parts.append(field_value.name)
                    else:
                        parts.append(field_value.display_name or field_value.name)
                
                elif field_meta.type == 'many2many':
                    # Optimización con mapped
                    names = field_value.mapped('name')
                    if names:
                        parts.append(", ".join(names)) # Coma se ve mejor en M2M
                        
                elif field_meta.type == 'selection':
                    # Truco pro: obtener el label del selection, no el key
                    parts.append(dict(product._fields[field_name].selection).get(field_value, field_value))
                    
                else:
                    parts.append(str(field_value))

            if parts:
                product.display_name = " ".join(parts)
            else:
                # Fallback al comportamiento nativo si la configuración no generó nada
                # (Para no dejar el producto sin nombre o con 'False')
                # Llamamos a super sobre un recordset de 1 elemento para evitar recursión infinita
                super()._compute_display_name()

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
