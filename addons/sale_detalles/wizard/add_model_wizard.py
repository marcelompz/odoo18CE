from odoo import models, fields, api

class AddModelWizard(models.TransientModel):
    _name = 'add.model.wizard'
    _description = 'Wizard para agregar nuevos modelos a la orden'

    order_id = fields.Many2one('sale.order', string='Orden', readonly=True, required=True)
    model_type_id = fields.Many2one('model.type', string='Tipo de Modelo', required=True)
    image = fields.Binary(string='Imagen del Modelo')
    quantity = fields.Float(string='Cantidad', default=1.0, required=True)
    notes = fields.Text(string='Notas Adicionales')
    
    # Nuevos campos importantes
    product_ids = fields.Many2many('product.template', string='Productos Relacionados', 
                                  domain=[('show_in_import_reference', '=', True)])
    designer_id = fields.Many2one('res.users', string='Diseñador Asignado')
    
    # Campos para mostrar información de la orden
    order_name = fields.Char(related='order_id.name', string='Número de Orden', readonly=True)
    partner_name = fields.Char(related='order_id.partner_id.name', string='Cliente', readonly=True)
    
    # Campo para indicar si es una modificación
    is_modification = fields.Boolean(string='Es una modificación', default=False)
    existing_model_line_id = fields.Many2one('order.detail.model.lines', string='Modelo existente a reemplazar')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get('default_order_id')
        if order_id:
            res['order_id'] = order_id
        return res

    @api.onchange('model_type_id')
    def _onchange_model_type_id(self):
        """Detectar si ya existe un modelo del mismo tipo en la orden"""
        if self.model_type_id and self.order_id:
            try:
                existing_model = self.env['order.detail.model.lines'].search([
                    ('order_id', '=', self.order_id.id),
                    ('model_type_id', '=', self.model_type_id.id)
                ], limit=1)
                
                if existing_model:
                    self.is_modification = True
                    self.existing_model_line_id = existing_model.id
                    # Pre-llenar con datos del modelo existente
                    self.quantity = existing_model.quantity
                    if existing_model.product_ids:
                        self.product_ids = [(6, 0, existing_model.product_ids.ids)]
                    if existing_model.current_designer_id:
                        self.designer_id = existing_model.current_designer_id.id
                else:
                    self.is_modification = False
                    self.existing_model_line_id = False
            except Exception as e:
                # Si hay algún error, no marcar como modificación
                self.is_modification = False
                self.existing_model_line_id = False

    @api.constrains('quantity')
    def _check_quantity(self):
        """Validar que la cantidad sea mayor a 0"""
        for record in self:
            if record.quantity <= 0:
                raise models.ValidationError('La cantidad debe ser mayor a 0.')

    def action_add_model(self):
        """Agrega el nuevo modelo a la orden o modifica uno existente"""
        for wizard in self:
            # Validaciones adicionales
            if not wizard.model_type_id:
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
            
            if wizard.quantity <= 0:
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
            
            try:
                if wizard.is_modification and wizard.existing_model_line_id:
                    # MODIFICACIÓN: Actualizar el modelo existente en lugar de eliminarlo
                    existing_model = wizard.existing_model_line_id
                    
                    # Guardar información anterior para el historial
                    old_info = {
                        'image': existing_model.image,
                        'quantity': existing_model.quantity,
                        'products': existing_model.product_ids.mapped('name'),
                        'designer': existing_model.current_designer_id.name if existing_model.current_designer_id else 'Sin diseñador'
                    }
                    
                    # Actualizar el modelo existente
                    update_vals = {
                        'image': wizard.image if wizard.image else existing_model.image,
                        'quantity': wizard.quantity,
                        'product_ids': [(6, 0, wizard.product_ids.ids)] if wizard.product_ids else existing_model.product_ids.ids
                    }
                    
                    existing_model.write(update_vals)
                    
                    # Crear entrada en el historial indicando la modificación
                    designer_for_history = wizard.designer_id or self.env.user
                    modification_history_vals = {
                        'model_line_id': existing_model.id,
                        'order_id': wizard.order_id.id,
                        'model_type_id': wizard.model_type_id.id,
                        'designer_id': designer_for_history.id,
                        'work_type': 'modification',
                        'notes': f'Modelo modificado. Cambios: Imagen {"actualizada" if wizard.image else "sin cambios"}, Cantidad: {old_info["quantity"]} → {wizard.quantity}, Productos: {", ".join(old_info["products"]) if old_info["products"] else "Sin productos"} → {", ".join(wizard.product_ids.mapped("name")) if wizard.product_ids else "Sin productos"}'
                    }
                    self.env['model.design.history'].create(modification_history_vals)
                    
                    # Si se asignó un nuevo diseñador, crear entrada adicional
                    if wizard.designer_id and wizard.designer_id != existing_model.current_designer_id:
                        designer_change_vals = {
                            'model_line_id': existing_model.id,
                            'order_id': wizard.order_id.id,
                            'model_type_id': wizard.model_type_id.id,
                            'designer_id': wizard.designer_id.id,
                            'work_type': 'modification',
                            'notes': f'Diseñador cambiado de {old_info["designer"]} a {wizard.designer_id.name}'
                        }
                        self.env['model.design.history'].create(designer_change_vals)
                    
                    # Mensaje de éxito para modificación
                    success_message = f'Modelo "{existing_model.model_type_id.name}" modificado correctamente'
                    if wizard.image:
                        success_message += ' (imagen actualizada)'
                    if wizard.designer_id:
                        success_message += f' y asignado al diseñador {wizard.designer_id.name}'
                    
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Éxito',
                            'message': success_message,
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                    
                else:
                    # CREACIÓN: Crear nueva línea de modelo
                    model_line_vals = {
                        'order_id': wizard.order_id.id,
                        'model_type_id': wizard.model_type_id.id,
                        'image': wizard.image,
                        'quantity': wizard.quantity,
                    }
                    
                    # Agregar productos solo si existen
                    if wizard.product_ids:
                        model_line_vals['product_ids'] = [(6, 0, wizard.product_ids.ids)]
                    
                    new_model_line = self.env['order.detail.model.lines'].create(model_line_vals)
                    
                    # Si se asignó un diseñador, crear el historial de diseño
                    if wizard.designer_id:
                        design_history_vals = {
                            'model_line_id': new_model_line.id,
                            'order_id': wizard.order_id.id,
                            'model_type_id': wizard.model_type_id.id,
                            'designer_id': wizard.designer_id.id,
                            'work_type': 'new',
                            'notes': wizard.notes or 'Modelo creado desde wizard'
                        }
                        self.env['model.design.history'].create(design_history_vals)
                    
                    # Mensaje de éxito para creación
                    success_message = f'Modelo "{new_model_line.model_type_id.name}" agregado correctamente'
                    if wizard.designer_id:
                        success_message += f' y asignado al diseñador {wizard.designer_id.name}'
                    if wizard.product_ids:
                        success_message += f' con {len(wizard.product_ids)} producto(s) relacionado(s)'
                    success_message += f' a la orden {wizard.order_id.name}'
                    
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Éxito',
                            'message': success_message,
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                
            except Exception as e:
                action_type = "modificar" if wizard.is_modification else "agregar"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': f'Error al {action_type} el modelo: {str(e)}',
                        'type': 'danger',
                        'sticky': False,
                    }
                }

    def action_cancel(self):
        """Acción para cancelar"""
        return {'type': 'ir.actions.act_window_close'} 