from odoo import models, fields, api
import base64

class ShowModelsWizard(models.TransientModel):
    _name = 'show.models.wizard'
    _description = 'Wizard para mostrar modelos con imagen grande'

    order_id = fields.Many2one('sale.order', string='Orden', readonly=True)
    model_lines_html = fields.Html(compute='_compute_model_lines_html')
    show_empty_message = fields.Boolean(compute='_compute_show_empty_message')
    
    # Campos para agregar nuevos modelos
    new_model_type_id = fields.Many2one('model.type', string='Nuevo Tipo de Modelo', required=False)
    new_model_image = fields.Binary(string='Imagen del Modelo')
    new_model_quantity = fields.Float(string='Cantidad', default=1.0)
    show_add_form = fields.Boolean(string='Mostrar Formulario de Agregar', default=False)

    @api.depends('order_id')
    def _compute_model_lines_html(self):
        for wizard in self:
            html = """
            <table style='width:100%; text-align:left;'>
                <tr><th>Modelo</th><th>Imagen</th></tr>
            """
            if wizard.order_id and wizard.order_id.model_line_ids:
                for line in wizard.order_id.model_line_ids:
                    img = ""
                    img_src = ""
                    if line.image:
                        img_src = f"data:image/png;base64,{line.image.decode() if isinstance(line.image, bytes) else line.image}"
                        img = f"<img src='{img_src}' style='max-width:550px; max-height:550px; vertical-align:middle;' class='img-fluid'/>"
                    html += f"<tr><td>{line.model_type_id.name or ''}</td><td>{img}</td></tr>"
            else:
                html += "<tr><td colspan='2'>No hay modelos asociados a esta orden.</td></tr>"
            html += """
            </table>
            """
            wizard.model_lines_html = html

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get('default_order_id')
        if order_id:
            res['order_id'] = order_id
        return res

    def _compute_show_empty_message(self):
        for wizard in self:
            wizard.show_empty_message = not bool(wizard.order_id.model_line_ids)
    
    def action_toggle_add_form(self):
        """Alterna la visibilidad del formulario de agregar modelo"""
        for wizard in self:
            wizard.show_add_form = not wizard.show_add_form
            if not wizard.show_add_form:
                # Limpiar campos cuando se oculta el formulario
                wizard.new_model_type_id = False
                wizard.new_model_image = False
                wizard.new_model_quantity = 1.0
    
    def action_add_model(self):
        """Agrega un nuevo modelo a la orden"""
        for wizard in self:
            if not wizard.new_model_type_id:
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
            
            try:
                # Crear la nueva línea de modelo
                model_line_vals = {
                    'order_id': wizard.order_id.id,
                    'model_type_id': wizard.new_model_type_id.id,
                    'image': wizard.new_model_image,
                    'quantity': wizard.new_model_quantity,
                }
                
                new_model_line = self.env['order.detail.model.lines'].create(model_line_vals)
                
                # Limpiar campos después de crear
                wizard.new_model_type_id = False
                wizard.new_model_image = False
                wizard.new_model_quantity = 1.0
                wizard.show_add_form = False
                
                # Forzar la recarga de los campos computados de manera más segura
                wizard._compute_model_lines_html()
                wizard._compute_show_empty_message()
                
                # Mostrar mensaje de éxito
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Éxito',
                        'message': f'Modelo "{new_model_line.model_type_id.name}" agregado correctamente',
                        'type': 'success',
                        'sticky': False,
                    }
                }
                
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': f'Error al agregar el modelo: {str(e)}',
                        'type': 'danger',
                        'sticky': False,
                    }
                } 