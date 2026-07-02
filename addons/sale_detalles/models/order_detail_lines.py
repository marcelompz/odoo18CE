from odoo import models, fields, api
from odoo.exceptions import ValidationError

class OrderDetailLines(models.Model):
    _name = 'order.detail.lines'
    _description = 'Líneas de Detalle de Órdenes'
    _order = 'order_id, sequence, id'

    sequence = fields.Integer(string='Orden', default=10, help="Secuencia para el orden de las líneas")
    order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True, ondelete='cascade')
    customer_name = fields.Char(string='Nombre del Cliente', related='order_id.partner_id.name', store=True)
    order_number = fields.Char(string='Número de Orden', related='order_id.name', store=True)
    user_id = fields.Many2one('res.users', string='Vendedor', related='order_id.user_id', store=True, readonly=True)
    manager_id = fields.Many2one('res.users', string='Gestor', related='order_id.manager_id', store=True, readonly=True)
    quantity = fields.Float(string='Cantidad', required=True, default=1.0)
    
    customer_model = fields.Many2one('model.type', string='Modelo de Cliente', required=True)
    
    name_customer = fields.Char(string='Nombre del Cliente')
    number_customer = fields.Char(string='Número de Cliente')
    other_customer = fields.Char(string='Otros Datos del Cliente')
    
    product1_variant_id = fields.Many2one('product.product', string='Variante Producto 1', ondelete='restrict', domain="[('sale_ok','=',True)]" )
    product2_variant_id = fields.Many2one('product.product', string='Variante Producto 2', ondelete='restrict', domain="[('sale_ok','=',True)]")
    product3_variant_id = fields.Many2one('product.product', string='Variante Producto 3', ondelete='restrict', domain="[('sale_ok','=',True)]")
    product4_variant_id = fields.Many2one('product.product', string='Variante Producto 4', ondelete='restrict', domain="[('sale_ok','=',True)]")
    product5_variant_id = fields.Many2one('product.product', string='Variante Producto 5', ondelete='restrict', domain="[('sale_ok','=',True)]")

    price = fields.Float(string='Precio Total', compute='_compute_price', store=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    sale_line_ids = fields.One2many('sale.order.line', 'order_detail_line_id', string='Líneas de Pedido')

    @api.depends('product1_variant_id', 'product2_variant_id', 'product3_variant_id', 
                 'product4_variant_id', 'product5_variant_id')
    def _compute_price(self):
        for record in self:
            total_price = 0.0
            if record.product1_variant_id:
                total_price += record.product1_variant_id.list_price
            if record.product2_variant_id:
                total_price += record.product2_variant_id.list_price
            if record.product3_variant_id:
                total_price += record.product3_variant_id.list_price
            if record.product4_variant_id:
                total_price += record.product4_variant_id.list_price
            if record.product5_variant_id:
                total_price += record.product5_variant_id.list_price
            record.price = total_price

    @api.depends('quantity', 'price')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.quantity * record.price

    def _update_price_from_sale_line(self):
        """Actualiza el precio total basado en las líneas de pedido"""
        for record in self:
            if not record.exists() or self.env.context.get('skip_price_update_recursion'):
                continue
                
            total_price = 0.0
            for line in record.sale_line_ids:
                if line.exists():
                    total_price += line.price_unit
                    
            # Solo actualizar si el precio ha cambiado
            if record.price != total_price:
                record.with_context(skip_price_update_recursion=True).write({
                    'price': total_price,
                    'subtotal': record.quantity * total_price
                })
                # Actualizar el total general en la orden de venta
                record.order_id._compute_total_general()

    def _create_sale_line(self, product_id, product_number):
        if not product_id or not self.order_id:
            return False
            
        # Asegurarnos de que tenemos el order_id
        order_id = self.order_id.id
        if not order_id:
            return False
            
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return False
            
        # Crear la línea de pedido con sudo y asegurando el order_id
        try:
            sale_line_vals = {
                'order_id': order_id,
                'product_id': product_id,
                'product_uom_qty': self.quantity or 1.0,
                'price_unit': product.list_price,
                'name': f'Detalle por Tallas - Producto {product_number} - {product.name}',
                'product_uom': product.uom_id.id,
                'order_detail_line_id': self.id,
                'product_number': product_number,  # Nuevo campo para identificar el número de producto
            }
            return self.env['sale.order.line'].sudo().create(sale_line_vals)
        except Exception as e:
            self.env.user.notify_warning(
                message=f'Error al crear línea de pedido: {str(e)}',
                title='Error'
            )
            return False

    @api.model_create_multi
    def create(self, vals_list):
        # Validar que order_id esté presente en todos los registros
        for vals in vals_list:
            if not vals.get('order_id'):
                # Intentar obtener order_id del contexto
                default_order_id = self.env.context.get('default_order_id')
                if default_order_id:
                    vals['order_id'] = default_order_id
                else:
                    raise ValidationError('El campo "Orden de Venta" es obligatorio para crear una línea de detalle.')
        
        # Asignar secuencia automáticamente si no se proporciona
        for vals in vals_list:
            if not vals.get('sequence') and vals.get('order_id'):
                # Obtener el siguiente número de secuencia para esta orden
                max_sequence = self.search([
                    ('order_id', '=', vals['order_id'])
                ], order='sequence desc', limit=1)
                vals['sequence'] = (max_sequence.sequence or 0) + 10
        
        # Primero creamos los registros sin las líneas de pedido
        records = super(OrderDetailLines, self).create(vals_list)
        
        # Luego actualizamos cada registro para crear las líneas de pedido
        for record in records:
            if not record.order_id:
                continue
                
            # Crear líneas de pedido para cada producto seleccionado
            product_fields = [
                ('product1_variant_id', 1),
                ('product2_variant_id', 2),
                ('product3_variant_id', 3),
                ('product4_variant_id', 4),
                ('product5_variant_id', 5)
            ]
            
            # Usar write para crear las líneas de pedido
            write_vals = {}
            for field, number in product_fields:
                product = getattr(record, field)
                if product:
                    write_vals[field] = product.id
            
            if write_vals:
                record.write(write_vals)
                    
        return records

    def write(self, vals):
        # Si estamos en una actualización recursiva, solo permitir la escritura básica
        if self.env.context.get('skip_price_update_recursion'):
            return super(OrderDetailLines, self).write(vals)
            
        # Identificar qué productos se están eliminando o agregando
        product_fields = [
            ('product1_variant_id', 1),
            ('product2_variant_id', 2),
            ('product3_variant_id', 3),
            ('product4_variant_id', 4),
            ('product5_variant_id', 5)
        ]
        
        for record in self:
            if not record.order_id:
                continue
                
            # Antes de la escritura, guardar los valores actuales
            old_products = {
                field: getattr(record, field).id if getattr(record, field) else False
                for field, _ in product_fields
            }
            
            # Realizar la escritura
            result = super(OrderDetailLines, self).write(vals)
            
            # Después de la escritura, verificar cambios en productos
            for field, number in product_fields:
                if field in vals:
                    new_product_id = vals[field]
                    old_product_id = old_products[field]
                    
                    # Si se eliminó un producto
                    if new_product_id is False and old_product_id:
                        # Buscar y eliminar solo la línea de pedido correspondiente
                        sale_line = record.sale_line_ids.filtered(
                            lambda l: l.product_id.id == old_product_id and l.product_number == number
                        )
                        if sale_line:
                            sale_line.with_context(bypass_detail_line_unlink=True).unlink()
                    
                    # Si se agregó un nuevo producto o se cambió
                    elif new_product_id:
                        # Verificar si ya existe una línea de pedido para este producto y número
                        existing_line = record.sale_line_ids.filtered(
                            lambda l: l.product_id.id == new_product_id and l.product_number == number
                        )
                        if not existing_line:
                            self._create_sale_line(new_product_id, number)
            
            # Actualizar cantidades si es necesario
            if 'quantity' in vals:
                for sale_line in record.sale_line_ids:
                    sale_line.with_context(skip_price_update_recursion=True).write({
                        'product_uom_qty': vals['quantity']
                    })
                
        return result

    def unlink(self):
        for record in self:
            # Primero borramos las líneas de pedido asociadas
            if record.sale_line_ids:
                record.sale_line_ids.with_context(bypass_detail_line_unlink=True).unlink()
        
        # Reordenar las secuencias de las líneas restantes
        for order in self.mapped('order_id'):
            remaining_lines = order.order_detail_lines.sorted('sequence')
            for i, line in enumerate(remaining_lines, 1):
                line.sequence = i * 10
                
        return super(OrderDetailLines, self).unlink()

    def action_reorder_sequences(self):
        """Reordenar las secuencias de todas las líneas de una orden"""
        for order in self.mapped('order_id'):
            lines = order.order_detail_lines.sorted('sequence')
            for i, line in enumerate(lines, 1):
                line.sequence = i * 10

    @api.onchange('product1_variant_id')
    def _onchange_product1_variant_id(self):
        return {'domain': {'product1_variant_id': [('sale_ok', '=', True)]}}

class OrderDetailModelLines(models.Model):
    _name = 'order.detail.model.lines'
    _description = 'Líneas de Modelos de Detalle'

    order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True, ondelete='cascade')
    model = fields.Selection([
        ('modelo1', 'Modelo 1'),
        ('modelo2', 'Modelo 2'),
        ('modelo3', 'Modelo 3'),
        ('modelo4', 'Modelo 4'),
        ('modelo5', 'Modelo 5'),
        ('modelo6', 'Modelo 6'),
        ('modelo7', 'Modelo 7'),
        ('modelo8', 'Modelo 8'),
        ('modelo9', 'Modelo 9'),
        ('modelo10', 'Modelo 10'),
        ('modelo11', 'Modelo 11'),
        ('modelo12', 'Modelo 12'),
        ('modelo13', 'Modelo 13'),
        ('modelo14', 'Modelo 14'),
        ('modelo15', 'Modelo 15'),
        ('modelo16', 'Modelo 16'),
        ('modelo17', 'Modelo 17'),
        ('modelo18', 'Modelo 18'),
        ('modelo19', 'Modelo 19'),
        ('modelo20', 'Modelo 20'),
    ], string='Modelo', required=True)
    image = fields.Binary(string='Imagen', attachment=True)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_detail_line_id = fields.Many2one('order.detail.lines', string='Línea de Detalle', ondelete='cascade')

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        if self.is_detail_line and self.order_detail_line_id and self.order_detail_line_id.exists():
            # Usar with_context para prevenir recursión
            self.order_detail_line_id.with_context(skip_price_update_recursion=True)._update_price_from_sale_line()

    def write(self, vals):
        result = super(SaleOrderLine, self).write(vals)
        if self.is_detail_line and self.order_detail_line_id and self.order_detail_line_id.exists():
            if 'price_unit' in vals:
                # Usar with_context para prevenir recursión
                self.order_detail_line_id.with_context(skip_price_update_recursion=True)._update_price_from_sale_line()
        return result

    def unlink(self):
        for record in self:
            if record.order_detail_line_id and not self.env.context.get('bypass_detail_line_unlink'):
                # No borramos la línea de detalle aquí para evitar recursión
                pass
        return super(SaleOrderLine, self).unlink()

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_detail_lines = fields.One2many('order.detail.lines', 'order_id', string='Detalles de Tallas')
    model_line_ids = fields.One2many('order.detail.model.lines', 'order_id', string='Líneas de Modelos')
    total_general = fields.Float(string='Total General', compute='_compute_total_general', store=True)

    @property
    def safe_order_detail_lines(self):
        return self.order_detail_lines or self.env['order.detail.lines']

    @api.depends('order_detail_lines.subtotal')
    def _compute_total_general(self):
        for order in self:
            total = sum(line.subtotal for line in order.order_detail_lines)
            order.total_general = total 