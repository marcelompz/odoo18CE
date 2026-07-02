from odoo import models, fields, api

class OrderDetailModelLines(models.Model):
    _name = 'order.detail.model.lines'
    _description = 'Líneas de Modelos'

    order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True)
    model_type_id = fields.Many2one('model.type', string='Modelo', required=True)
    image = fields.Binary(string='Imagen', attachment=True)
    sale_line_ids = fields.One2many('sale.order.line', 'model_line_id', string='Líneas de Venta')
    quantity = fields.Float(string='Cantidad', default=1.0)
    design_history_ids = fields.One2many('model.design.history', 'model_line_id', string='Historial de Diseño')
    current_designer_id = fields.Many2one('res.users', string='Diseñador Actual', compute='_compute_current_designer', store=True)
    has_designer = fields.Boolean(compute='_compute_has_designer', store=True)
    work_type = fields.Selection([
        ('new', 'Nuevo'),
        ('modification', 'Modificaciones')
    ], string='Tipo de Trabajo', compute='_compute_work_type', store=True)
    product_ids = fields.Many2many('product.template', string='Productos Relacionados', 
                                  domain=[('show_in_import_reference', '=', True)])
    
    # Nuevos campos para el formulario
    partner_name = fields.Char(related='order_id.partner_id.name', string='Cliente', readonly=True)
    notes = fields.Text(string='Notas Adicionales')
    designer_id = fields.Many2one('res.users', string='Diseñador Asignado')

    @api.depends('design_history_ids.designer_id', 'design_history_ids.date')
    def _compute_current_designer(self):
        for record in self:
            latest_history = record.design_history_ids.sorted('date', reverse=True)[:1]
            record.current_designer_id = latest_history.designer_id if latest_history else False

    @api.depends('current_designer_id')
    def _compute_has_designer(self):
        for record in self:
            record.has_designer = bool(record.current_designer_id)

    @api.depends('design_history_ids')
    def _compute_work_type(self):
        for record in self:
            record.work_type = 'new' if not record.design_history_ids else 'modification'

    @api.onchange('model_type_id')
    def _onchange_model_type_id(self):
        if self.model_type_id and self.order_id:
            # Verificar si ya existe un modelo del mismo tipo en la orden
            existing_model = self.env['order.detail.model.lines'].search([
                ('order_id', '=', self.order_id.id),
                ('model_type_id', '=', self.model_type_id.id),
                ('id', '!=', self.id)  # Excluir el registro actual si es una edición
            ], limit=1)
            
            if existing_model:
                return {
                    'warning': {
                        'title': 'Modelo Duplicado',
                        'message': f'Ya existe un modelo del tipo "{self.model_type_id.name}" en esta orden. Considere modificar el existente en lugar de crear uno nuevo.',
                    }
                }
        
        # Limpiar las líneas de venta existentes
        self.sale_line_ids = [(5, 0, 0)]

    @api.constrains('quantity')
    def _check_quantity(self):
        """Validar que la cantidad sea mayor a 0"""
        for record in self:
            if record.quantity <= 0:
                raise models.ValidationError('La cantidad debe ser mayor a 0.')

    def action_assign_designer(self):
        """Abrir wizard para asignar diseñador"""
        # Verificar si la orden está bloqueada
        if self.order_id.state == 'sale':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Orden Bloqueada',
                    'message': 'No se puede asignar un diseñador a una orden confirmada.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'name': 'Asignar Diseñador',
            'type': 'ir.actions.act_window',
            'res_model': 'model.design.history',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model_line_id': self.id,
                'default_order_id': self.order_id.id,
                'default_model_type_id': self.model_type_id.id if self.model_type_id else False,
                'default_work_type': 'new' if not self.design_history_ids else 'modification'
            }
        }

    def action_save_and_close(self):
        """Guardar y cerrar el formulario"""
        if not self.model_type_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Debe seleccionar un tipo de modelo',
                    'type': 'danger',
                    'sticky': False,
                }
            }
        
        if self.quantity <= 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'La cantidad debe ser mayor a 0',
                    'type': 'danger',
                    'sticky': False,
                }
            }
        
        # Si se asignó un diseñador, crear el historial de diseño
        if self.designer_id:
            design_history_vals = {
                'model_line_id': self.id,
                'order_id': self.order_id.id,
                'model_type_id': self.model_type_id.id,
                'designer_id': self.designer_id.id,
                'work_type': 'new' if not self.design_history_ids else 'modification',
                'notes': self.notes or 'Modelo creado/actualizado desde formulario'
            }
            self.env['model.design.history'].create(design_history_vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': f'Modelo "{self.model_type_id.name}" guardado correctamente',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_save_and_new(self):
        """Guardar y crear uno nuevo"""
        result = self.action_save_and_close()
        
        # Crear nuevo registro
        new_record = self.create({
            'order_id': self.order_id.id,
            'model_type_id': False,
            'quantity': 1.0,
            'image': False,
            'product_ids': [(6, 0, [])],
            'notes': '',
            'designer_id': False,
        })
        
        # Abrir el nuevo registro
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agregar Modelo',
            'res_model': 'order.detail.model.lines',
            'view_mode': 'form',
            'res_id': new_record.id,
            'target': 'current',
            'context': {'default_order_id': self.order_id.id}
        }

    def _update_price_from_sale_line(self):
        """Actualizar el precio desde la línea de venta"""
        pass  # Implementar si es necesario 