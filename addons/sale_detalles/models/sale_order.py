from odoo import models, fields, api
import html

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manager_id = fields.Many2one('res.users', string='Gestor', default=lambda self: self.env.user)
    
    stage_id = fields.Many2one('sale.stage', string='Etapa', tracking=True, group_expand='_read_group_stage_id')
    order_detail_lines = fields.One2many('order.detail.lines', 'order_id', string='Detalles de Tallas')
    model_line_ids = fields.One2many('order.detail.model.lines', 'order_id', string='Líneas de Modelos')
    customer_model = fields.Char(string='Modelo del Cliente', tracking=True)
    name_customer = fields.Char(string='Nombre del Cliente', tracking=True)
    number_customer = fields.Char(string='Número del Cliente', tracking=True)
    other_customer = fields.Char(string='Otros Datos del Cliente', tracking=True)
    general_description = fields.Html(string='Descripción General')
    sale_order_line_summary_html = fields.Html(
        string="Resumen de líneas de pedido",
        compute='_compute_sale_order_line_summary_html'
    )
    
    # Campo para la vista de calendario
    total_products_count = fields.Integer(
        string='Total de Productos',
        compute='_compute_total_products_count',
        store=True
    )
    
    # Nuevos campos de fechas
    confirmation_date = fields.Date(string='Fecha de Confirmación', tracking=True)
    validity_date = fields.Date(string='Fecha de Vencimiento', tracking=True)
    date_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('valid', 'Válido'),
        ('invalid', 'Inválido'),
        ('overdue', 'Vencido')
    ], string='Estado de Fechas', compute='_compute_date_status', store=True)
    
    # Campo para identificar vista de diseñador
    is_designer_view = fields.Boolean(string='Es Vista de Diseñador', default=False, help='Indica si esta orden se está viendo en la vista de diseñador')

    @api.constrains('confirmation_date', 'validity_date')
    def _check_dates(self):
        for record in self:
            if record.confirmation_date and record.validity_date:
                if record.confirmation_date >= record.validity_date:
                    raise models.ValidationError(
                        'La fecha de confirmación debe ser menor a la fecha de vencimiento.'
                    )

    @api.onchange('confirmation_date', 'validity_date')
    def _onchange_dates(self):
        if self.confirmation_date and self.validity_date:
            if self.confirmation_date >= self.validity_date:
                return {
                    'warning': {
                        'title': 'Fechas Inválidas',
                        'message': 'La fecha de confirmación debe ser menor a la fecha de vencimiento.',
                    }
                }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('stage_id'):
                stage = self.env['sale.stage'].search([('sequence', '=', 1)], limit=1)
                if stage:
                    vals['stage_id'] = stage.id
        return super().create(vals_list)

    def write(self, vals):
        if 'stage_id' in vals:
            stage = self.env['sale.stage'].browse(vals['stage_id'])
            if stage.is_done:
                vals['state'] = 'done'
            elif stage.is_cancel:
                vals['state'] = 'cancel'
        
        # Establecer fecha de confirmación automáticamente si se confirma la orden
        if 'state' in vals and vals['state'] == 'sale' and not self.confirmation_date:
            vals['confirmation_date'] = fields.Date.today()
            
        return super().write(vals)

    def action_confirm(self):
        """Sobrescribir el método de confirmación para validar validity_date y establecer la fecha automáticamente"""
        # Validar validity_date antes de confirmar
        for order in self:
            if order.validity_date:
                config = self.env['sale.detalles.config'].search([('active', '=', True)], limit=1)
                if config:
                    is_valid, message = config.check_validity_date_approval(order.validity_date)
                    if not is_valid:
                        raise models.ValidationError(message)
            else:
                raise models.ValidationError('La fecha de vencimiento (validity_date) es obligatoria para confirmar la venta.')
        
        result = super().action_confirm()
        for order in self:
            if not order.confirmation_date:
                order.confirmation_date = fields.Date.today()
        return result

    def open_show_models_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modelos',
            'res_model': 'show.models.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def open_view_models(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modelos de la Orden',
            'res_model': 'order.detail.model.lines',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def open_show_description_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Descripción General',
            'res_model': 'show.description.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def open_designer_view(self):
        """Abrir la vista de diseñador (solo modelos e información técnica)"""
        # Marcar esta orden como vista de diseñador
        self.write({'is_designer_view': True})
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vista Diseñador - Modelos e Información Técnica',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'view_id': self.env.ref('sale_detalles.view_order_detail_form').id,
            'res_id': self.id,
            'target': 'current',
            'context': {
                'default_is_designer_view': True,
                'force_designer_view': True,
                'form_view_initial_mode': 'edit'
            }
        }

    def reset_designer_view(self):
        """Resetear el campo de vista de diseñador"""
        self.write({'is_designer_view': False})
        return True

    def action_date_management_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gestión de Fechas',
            'res_model': 'date.management.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_ids': [(6, 0, [self.id])]},
        }

    def action_reorder_sequences(self):
        """Reordenar las secuencias de las líneas de detalle"""
        for line in self.order_detail_lines:
            line.action_reorder_sequences()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Secuencias Reordenadas',
                'message': f'Se han reordenado las secuencias de {len(self.order_detail_lines)} líneas.',
                'type': 'success',
            }
        }

    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_sale_order_line_summary_html(self):
        for order in self:
            summary = {}
            for line in order.order_line:
                key = line.product_id
                summary.setdefault(key, 0)
                summary[key] += line.product_uom_qty
            html_str = "<table class='table table-sm'><tr><th>Producto</th><th>Cantidad Total</th></tr>"
            for product in sorted(summary, key=lambda p: p.name):
                html_str += f"<tr><td>{html.escape(product.display_name)}</td><td>{summary[product]}</td></tr>"
            html_str += "</table>" if summary else "<i>No hay productos en el pedido</i>"
            order.sale_order_line_summary_html = html_str

    @api.depends('order_line.product_uom_qty', 'order_detail_lines.quantity')
    def _compute_total_products_count(self):
        """Calcula el total de productos incluyendo líneas de venta y detalles de tallas"""
        for order in self:
            total = 0
            # Sumar productos de las líneas de venta
            for line in order.order_line:
                total += line.product_uom_qty
            # Sumar productos de los detalles de tallas
            for detail in order.order_detail_lines:
                total += detail.quantity
            order.total_products_count = total

    @api.depends('confirmation_date', 'validity_date')
    def _compute_date_status(self):
        today = fields.Date.today()
        for record in self:
            if not record.confirmation_date or not record.validity_date:
                record.date_status = 'pending'
            elif record.confirmation_date >= record.validity_date:
                record.date_status = 'invalid'
            elif record.validity_date < today:
                record.date_status = 'overdue'
            else:
                record.date_status = 'valid'

    @api.model
    def _read_group_stage_id(self, stages, domain, order=None):
        return self.env['sale.stage'].search([])

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_detail_line_id = fields.Many2one('order.detail.lines', string='Línea de Detalle')
    model_line_id = fields.Many2one('order.detail.model.lines', string='Línea de Modelo')
    is_detail_line = fields.Boolean(string='Es Línea de Detalle', compute='_compute_is_detail_line', store=True)

    @api.depends('order_detail_line_id', 'model_line_id')
    def _compute_is_detail_line(self):
        for line in self:
            line.is_detail_line = bool(line.order_detail_line_id or line.model_line_id)

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        if self.is_detail_line:
            return {
                'warning': {
                    'title': 'Cantidad Bloqueada',
                    'message': 'La cantidad no puede ser modificada en líneas de detalle.',
                },
                'value': {'product_uom_qty': self.order_detail_line_id.quantity if self.order_detail_line_id else self.model_line_id.quantity}
            }
        return {}

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        if self.is_detail_line and self.order_detail_line_id:
            # Actualizar el precio en la línea de detalle
            self.order_detail_line_id._update_price_from_sale_line()

    def write(self, vals):
        if self.is_detail_line and 'product_uom_qty' in vals:
            # Prevenir cambios en la cantidad para líneas de detalle
            vals['product_uom_qty'] = self.order_detail_line_id.quantity if self.order_detail_line_id else self.model_line_id.quantity
        result = super().write(vals)
        if self.is_detail_line and 'price_unit' in vals:
            if self.order_detail_line_id:
                self.order_detail_line_id._update_price_from_sale_line()
            elif self.model_line_id:
                self.model_line_id._update_price_from_sale_line()
        return result

    def unlink(self):
        for record in self:
            if record.order_detail_line_id and not self.env.context.get('bypass_detail_line_unlink'):
                record.order_detail_line_id.unlink()
        return super().unlink() 