# -*- coding: utf-8 -*-

import unicodedata
from odoo import models, fields, api, _
from odoo.exceptions import UserError


def normalize_text(text):
    """
    Normaliza texto para comparación: minúsculas, sin tildes, sin espacios extra.
    Ejemplo: "Artículos de Electricidad" → "articulos de electricidad"
    """
    if not text:
        return ''
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = ' '.join(text.split())
    return text


def find_best_match_category(category_name, categories_env):
    """
    Busca una categoría existente con nombre similar (fuzzy match).
    """
    if not category_name:
        return None
    
    normalized_input = normalize_text(category_name)
    all_categories = categories_env.search([])
    
    # 1. Búsqueda exacta normalizada
    for categ in all_categories:
        if normalize_text(categ.name) == normalized_input:
            return categ
    
    # 2. Búsqueda por contención
    for categ in all_categories:
        normalized_categ = normalize_text(categ.name)
        if normalized_categ and normalized_categ in normalized_input:
            return categ
        if normalized_input and normalized_input in normalized_categ:
            return categ
    
    # 3. Búsqueda por similaridad de palabras (80%)
    input_words = set(normalized_input.split())
    for categ in all_categories:
        normalized_categ = normalize_text(categ.name)
        categ_words = set(normalized_categ.split())
        
        if not categ_words or not input_words:
            continue
        
        common_words = input_words & categ_words
        total_words = input_words | categ_words
        
        if len(total_words) > 0:
            similarity = len(common_words) / len(total_words)
            if similarity >= 0.8:
                return categ
    
    return None


class ProductBatchImport(models.Model):
    _name = 'product.batch.import'
    _description = 'Importación de Productos en Lote desde Odoo'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Referencia', required=True, copy=False, default='Nuevo')
    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de Inventario',
        required=True,
        domain=[('usage', '=', 'internal')],
        help="Ubicación física donde se cargará el stock inicial por defecto."
    )
    line_ids = fields.One2many('product.batch.import.line', 'batch_id', string='Líneas')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('done', 'Completado'),
        ('cancel', 'Cancelado'),
    ], default='draft', string='Estado', tracking=True)
    product_count = fields.Integer(compute='_compute_product_count', string='Cantidad de Productos')
    valid_count = fields.Integer(compute='_compute_valid_invalid_count', string='Productos Válidos')
    invalid_count = fields.Integer(compute='_compute_valid_invalid_count', string='Con Errores')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('product.batch.import') or 'Nuevo'
        return super(ProductBatchImport, self).create(vals)

    def _compute_product_count(self):
        for batch in self:
            batch.product_count = len(batch.line_ids)

    def _compute_valid_invalid_count(self):
        for batch in self:
            batch.valid_count = len(batch.line_ids.filtered(lambda l: l.is_valid))
            batch.invalid_count = len(batch.line_ids.filtered(lambda l: not l.is_valid))

    def action_validate(self):
        """Validate all lines and check for errors"""
        for batch in self:
            for line in batch.line_ids:
                line.action_validate()
            batch.state = 'validated'
        return True

    def action_confirm(self):
        """Confirm and create products - OPTIMIZED with batch processing + FUZZY MATCH"""
        for batch in self:
            valid_lines = batch.line_ids.filtered(lambda l: l.is_valid)
            if not valid_lines:
                raise UserError(_("No hay líneas válidas para procesar"))

            # PRECARGAR CATEGORÍAS - Una sola consulta con FUZZY MATCH
            unique_categ_names = set(valid_lines.mapped('categ_name'))
            categories_cache = {}
            categories_created = []
            categories_matched = []
            
            for categ_name in unique_categ_names:
                if categ_name:
                    # 1. Intentar fuzzy match con categorías existentes
                    category = find_best_match_category(categ_name, self.env['product.category'])
                    
                    if category:
                        # Encontró categoría similar
                        categories_matched.append((categ_name, category.name))
                    else:
                        # No encontró similar, crear nueva
                        category = self.env['product.category'].create({'name': categ_name})
                        categories_created.append(categ_name)
                    
                    categories_cache[categ_name] = category

            # PRECARGAR CATEGORÍAS PdV con FUZZY MATCH
            unique_pos_categ_names = set(valid_lines.mapped('pos_categ_name'))
            pos_categories_cache = {}
            pos_categories_created = []
            pos_categories_matched = []
            
            for pos_categ_name in unique_pos_categ_names:
                if pos_categ_name and 'pos.category' in self.env:
                    # 1. Intentar fuzzy match con categorías existentes
                    pos_category = find_best_match_category(pos_categ_name, self.env['pos.category'])
                    
                    if pos_category:
                        # Encontró categoría similar
                        pos_categories_matched.append((pos_categ_name, pos_category.name))
                    else:
                        # No encontró similar, crear nueva
                        pos_category = self.env['pos.category'].create({'name': pos_categ_name})
                        pos_categories_created.append(pos_categ_name)
                    
                    pos_categories_cache[pos_categ_name] = pos_category

            # CREACIÓN MASIVA DE PRODUCTOS - Batch processing
            product_vals_list = []
            products_to_quant = []
            
            for line in valid_lines:
                categ_id = self.env.ref('product.product_category_all').id
                if line.categ_name and line.categ_name in categories_cache:
                    categ_id = categories_cache[line.categ_name].id

                pos_categ_id = False
                if line.pos_categ_name and line.pos_categ_name in pos_categories_cache:
                    pos_categ_id = pos_categories_cache[line.pos_categ_name].id

                product_vals = {
                    'name': line.name,
                    'default_code': line.default_code,
                    'barcode': line.barcode or False,
                    'list_price': line.list_price,
                    'standard_price': line.standard_price,
                    'type': line.product_type,
                    'categ_id': categ_id,
                    'tracking': line.tracking,
                    'available_in_pos': line.available_in_pos,
                }

                if line.pos_description:
                    product_vals['description_sale'] = line.pos_description

                if pos_categ_id:
                    product_vals['pos_categ_id'] = pos_categ_id

                product_vals_list.append(product_vals)
                
                # Guardar referencia para inventario
                if line.qty_on_hand > 0:
                    products_to_quant.append((len(product_vals_list) - 1, line.qty_on_hand))

            # Creación masiva en una sola operación
            created_products = self.env['product.product'].create(product_vals_list)

            # APLICAR INVENTARIO MASIVO - Batch processing
            if products_to_quant and batch.location_id:
                quant_vals_list = []
                for idx, qty in products_to_quant:
                    product = created_products[idx]
                    quant_vals_list.append({
                        'product_id': product.id,
                        'location_id': batch.location_id.id,
                        'inventory_quantity': qty,
                    })
                
                # Creación masiva de quants
                quants = self.env['stock.quant'].with_context(inventory_mode=True).create(quant_vals_list)
                # Aplicar inventario
                for quant in quants:
                    quant.action_apply_inventory()

            batch.state = 'done'

            # Post message con detalle de categorías
            message = _('Se crearon %d productos exitosamente.') % len(created_products)
            
            if categories_matched:
                matched_list = ', '.join([f'"{orig}" → "{match}"' for orig, match in categories_matched])
                message += f'\n\n📁 Categorías reutilizadas (fuzzy match): {matched_list}'
            
            if categories_created:
                created_list = ', '.join(categories_created)
                message += f'\n📁 Categorías creadas: {created_list}'
            
            if pos_categories_matched:
                matched_list = ', '.join([f'"{orig}" → "{match}"' for orig, match in pos_categories_matched])
                message += f'\n🏪 Categorías PdV reutilizadas: {matched_list}'
            
            if pos_categories_created:
                created_list = ', '.join(pos_categories_created)
                message += f'\n🏪 Categorías PdV creadas: {created_list}'

            batch.message_post(body=message)

        return True

    def action_cancel(self):
        self.state = 'cancel'
        return True

    def action_reset_draft(self):
        self.state = 'draft'
        return True

    def action_add_line(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Agregar Línea'),
            'res_model': 'product.batch.import.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_batch_id': self.id},
        }

    def action_duplicate_valid_lines(self):
        """Duplicate this batch with only valid lines for correction"""
        self.ensure_one()
        valid_lines = self.line_ids.filtered(lambda l: l.is_valid)
        if not valid_lines:
            raise UserError(_("No hay líneas válidas para duplicar"))

        new_batch = self.copy({
            'name': 'Nuevo',
            'state': 'draft',
            'line_ids': False,
        })

        for line in valid_lines:
            line.copy({'batch_id': new_batch.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Importación en Lote'),
            'res_model': 'product.batch.import',
            'res_id': new_batch.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductBatchImportLine(models.Model):
    _name = 'product.batch.import.line'
    _description = 'Línea de Importación de Productos en Lote'
    _order = 'sequence, id'

    batch_id = fields.Many2one('product.batch.import', string='Importación en Lote', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    default_code = fields.Char(string='Referencia Interna', required=True)
    name = fields.Char(string='Nombre del Producto', required=True)
    pos_description = fields.Char(string='Descripción para PdV')
    barcode = fields.Char(string='Código de Barras')
    available_in_pos = fields.Boolean(string='Disponible en PdV', default=True)
    categ_name = fields.Char(string='Categoría de Producto')
    pos_categ_name = fields.Char(string='Categoría de PdV')
    list_price = fields.Float(string='Precio de Venta', default=0.0)
    standard_price = fields.Float(string='Precio de Costo', default=0.0)
    qty_on_hand = fields.Float(string='Cantidad a la Mano', default=0.0)
    product_type = fields.Selection([
        ('consu', 'Bienes (Almacenable/Consumible)'),
        ('service', 'Servicio'),
        ('combo', 'Combo'),
    ], string='Tipo de Producto', default='consu')
    tracking = fields.Selection([
        ('none', 'Ninguno'),
        ('lot', 'Por Lote'),
        ('serial', 'Por Número de Serie'),
    ], string='Trazabilidad', default='none')
    is_valid = fields.Boolean(string='Válido', compute='_compute_validation', store=True)
    error_message = fields.Text(string='Errores', compute='_compute_validation', store=True)
    product_id = fields.Many2one('product.product', string='Producto Creado', readonly=True)

    @api.depends('default_code', 'name', 'barcode', 'list_price', 'standard_price', 'qty_on_hand')
    def _compute_validation(self):
        for line in self:
            error_msgs = []

            # Check required fields
            if not line.default_code:
                error_msgs.append("Referencia interna requerida")

            if not line.name:
                error_msgs.append("Nombre requerido")

            # Check barcode uniqueness
            if line.barcode:
                existing = self.env['product.product'].search([('barcode', '=', line.barcode)], limit=1)
                if existing:
                    error_msgs.append(f"Código duplicado: {existing.name}")

            # Check negative values (only if provided, 0 is valid)
            if line.list_price < 0:
                error_msgs.append("Precio de venta no puede ser negativo")

            if line.standard_price < 0:
                error_msgs.append("Precio de costo no puede ser negativo")

            if line.qty_on_hand < 0:
                error_msgs.append("Cantidad no puede ser negativa")

            line.error_message = ', '.join(error_msgs) if error_msgs else False
            line.is_valid = len(error_msgs) == 0

    def action_validate(self):
        """Force validation refresh"""
        self._compute_validation()
        return True

    def action_delete(self):
        self.unlink()
        return True
