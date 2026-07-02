# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PortalDetailItem(models.Model):
    _name = 'portal.detail.item'
    _description = 'Item de Lista Portal'
    _order = 'id'

    list_id = fields.Many2one('portal.detail.list', 'Lista', required=True, ondelete='cascade')
    order_id = fields.Many2one('sale.order', 'Pedido', related='list_id.order_id', store=True)
    customer_id = fields.Many2one('res.partner', 'Cliente', related='list_id.customer_id', store=True)

    # Información del item
    modelo = fields.Char('Modelo', required=True)
    nombre = fields.Char('Nombre', required=True)
    numero = fields.Char('Número')
    otros = fields.Char('Otros')
    cantidad = fields.Integer('Cantidad', default=1)

    # Productos (hasta 5 por item)
    producto1 = fields.Char('Producto 1')
    talle1 = fields.Char('Talle 1')
    producto2 = fields.Char('Producto 2')
    talle2 = fields.Char('Talle 2')
    producto3 = fields.Char('Producto 3')
    talle3 = fields.Char('Talle 3')
    producto4 = fields.Char('Producto 4')
    talle4 = fields.Char('Talle 4')
    producto5 = fields.Char('Producto 5')
    talle5 = fields.Char('Talle 5')

    # Estado del item
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado')
    ], default='pending', tracking=True)

    commercial_notes = fields.Text('Observaciones del Comercial')

    # Fechas
    create_date = fields.Datetime('Fecha de Creación', readonly=True)
    write_date = fields.Datetime('Última Modificación', readonly=True)

    # Campos calculados
    products_summary = fields.Char('Resumen Productos', compute='_compute_products_summary')

    @api.depends('producto1', 'talle1', 'producto2', 'talle2', 'producto3', 'talle3', 'producto4', 'talle4', 'producto5', 'talle5')
    def _compute_products_summary(self):
        for record in self:
            products = []
            for i in range(1, 6):
                producto = getattr(record, f'producto{i}', False)
                talle = getattr(record, f'talle{i}', False)
                if producto:
                    if talle:
                        products.append(f"{producto} - {talle}")
                    else:
                        products.append(producto)
            
            record.products_summary = ', '.join(products) if products else 'Sin productos'

    def action_approve(self):
        """Aprobar item"""
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        """Rechazar item"""
        for record in self:
            record.state = 'rejected'

    def action_reset(self):
        """Resetear a pendiente"""
        for record in self:
            record.state = 'pending'

    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.modelo} - {record.nombre}"
            if record.cantidad > 1:
                name += f" (x{record.cantidad})"
            result.append((record.id, name))
        return result

    @api.constrains('cantidad')
    def _check_cantidad(self):
        """Validar cantidad positiva"""
        for record in self:
            if record.cantidad <= 0:
                raise ValueError(_('La cantidad debe ser mayor a cero.'))

    @api.constrains('modelo', 'nombre')
    def _check_required_fields(self):
        """Validar campos requeridos"""
        for record in self:
            if not record.modelo or not record.nombre:
                raise ValueError(_('El modelo y nombre son campos requeridos.'))

    def _get_products_data(self):
        """Obtener datos de productos en formato diccionario"""
        self.ensure_one()
        products = []
        for i in range(1, 6):
            producto = getattr(self, f'producto{i}', False)
            talle = getattr(self, f'talle{i}', False)
            if producto:
                products.append({
                    'producto': producto,
                    'talle': talle or '',
                    'position': i
                })
        return products

    def _set_products_data(self, products_data):
        """Establecer datos de productos desde diccionario"""
        self.ensure_one()
        # Limpiar productos existentes
        for i in range(1, 6):
            setattr(self, f'producto{i}', False)
            setattr(self, f'talle{i}', False)
        
        # Establecer nuevos productos
        for product_data in products_data[:5]:  # Máximo 5 productos
            position = product_data.get('position', 1)
            if 1 <= position <= 5:
                setattr(self, f'producto{position}', product_data.get('producto', ''))
                setattr(self, f'talle{position}', product_data.get('talle', ''))
