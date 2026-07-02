from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class MrpProductionWizardWorkcenter(models.TransientModel):
    _name = 'mrp.production.wizard.workcenter'
    _description = 'Centros de trabajo del wizard (Legacy)'

    wizard_id = fields.Many2one('mrp.production.wizard', string='Wizard', required=True, ondelete='cascade')
    category_id = fields.Many2one('product.category', string='Categoría')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de Trabajo', required=True)
    duration = fields.Float(string='Duración (minutos)', required=True)
    sequence = fields.Integer(string='Secuencia', required=True)
    operation_ids = fields.Many2many('mrp.routing.workcenter', string='Operaciones')
    operation_date = fields.Datetime(string='Fecha de Operación')

    @api.onchange('workcenter_id')
    def _onchange_workcenter_id(self):
        if self.workcenter_id:
            # Obtener todas las operaciones que usan este centro de trabajo
            operations = self.env['mrp.routing.workcenter'].search([
                ('workcenter_id', '=', self.workcenter_id.id)
            ])
            self.operation_ids = operations
            # Calcular la duración total
            self.duration = sum(operation.time_cycle_manual or 60 for operation in operations)

    @api.constrains('operation_ids')
    def _check_duplicate_operations(self):
        for record in self:
            if record.wizard_id:
                # Obtener todas las operaciones de otros centros de trabajo en el mismo wizard
                other_operations = record.wizard_id.workcenter_line_ids.filtered(
                    lambda l: l.id != record.id
                ).mapped('operation_ids')
                
                # Verificar si hay operaciones duplicadas
                duplicate_operations = record.operation_ids & other_operations
                if duplicate_operations:
                    raise UserError(_(
                        'Las siguientes operaciones ya están asignadas a otro centro de trabajo:\n%s'
                    ) % '\n'.join(duplicate_operations.mapped('name')))

class MrpProductionWizard(models.TransientModel):
    _name = 'mrp.production.wizard'
    _description = 'Wizard para crear órdenes de fabricación desde ventas'

    @api.model
    def default_get(self, fields_list):
        res = super(MrpProductionWizard, self).default_get(fields_list)
        
        # Primero, establecer el producto por defecto desde la configuración
        config_product_id = self.env['ir.config_parameter'].sudo().get_param('mrp_group_by_category.default_product_id')
        if config_product_id and 'product_id' in fields_list:
            res['product_id'] = int(config_product_id)
            
        # Luego, si venimos de una orden de venta, procesar sus líneas
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id'):
            sale_order = self.env['sale.order'].browse(self._context['active_id'])
            res['sale_order_id'] = sale_order.id
            
            operation_lines = []
            material_lines = []
            processed_operations = set()
            material_dict = {}
            current_date = fields.Datetime.now()

            # Iterar sobre las líneas de la orden de venta
            for line in sale_order.order_line.filtered(lambda l: l.product_id.bom_ids):
                # Recopilar operaciones únicas
                for bom in line.product_id.bom_ids:
                    for operation in bom.operation_ids:
                        operation_key = (operation.id, operation.workcenter_id.id)
                        if operation_key not in processed_operations:
                            duration = operation.time_cycle_manual or 60
                            operation_lines.append((0, 0, {
                                'name': operation.name,
                                'workcenter_id': operation.workcenter_id.id,
                                'operation_id': operation.id,
                                'duration': duration,
                                'sequence': operation.sequence,
                                'date_start': current_date,
                                'date_finished': current_date + timedelta(minutes=duration)
                            }))
                            current_date += timedelta(minutes=duration)
                            processed_operations.add(operation_key)
                
                # Recopilar y agrupar materiales
                for bom in line.product_id.bom_ids:
                    for bom_line in bom.bom_line_ids:
                        key = (bom_line.product_id.id, bom_line.product_uom_id.id)
                        if key not in material_dict:
                            material_dict[key] = {
                                'product_id': bom_line.product_id.id,
                                'product_uom_id': bom_line.product_uom_id.id,
                                'category_id': line.product_id.categ_id.id,  # Categoría de la línea de pedido
                                'product_qty': 0
                            }
                        material_dict[key]['product_qty'] += bom_line.product_qty * line.product_uom_qty
            
            # Crear las líneas de materiales a partir del diccionario agrupado
            for data in material_dict.values():
                material_lines.append((0, 0, data))

            res.update({
                'operation_line_ids': operation_lines,
                'material_line_ids': material_lines,
            })
            
        return res

    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta', readonly=True)
    start_date = fields.Date(string='Fecha de Inicio', default=fields.Date.context_today, required=True)
    product_id = fields.Many2one('product.product', string='Producto Principal', required=True)
    product_qty = fields.Float(string='Cantidad a fabricar', required=True, default=1.0)
    fecha_entrega = fields.Datetime(string='Fecha de Entrega', compute='_compute_fecha_entrega', store=False)
    category_ids = fields.Many2many('product.category', string='Categorías')
    
    # Campos para control de presupuesto
    budget_amount = fields.Float(string='Presupuesto', default=0.0, help='Presupuesto máximo para materiales')
    material_cost_total = fields.Float(string='Costo Total Materiales', compute='_compute_material_cost_total', store=False)
    budget_status = fields.Selection([
        ('ok', 'Dentro del Presupuesto'),
        ('warning', 'Presupuesto Excedido (Aceptable)'),
        ('error', 'Presupuesto Excedido (Rechazado)')
    ], string='Estado del Presupuesto', compute='_compute_budget_status', store=False)
    budget_exceeded_percent = fields.Float(string='% Excedido del Presupuesto', compute='_compute_budget_status', store=False)
    
    # Campo temporal para mantener compatibilidad
    workcenter_line_ids = fields.One2many(
        'mrp.production.wizard.workcenter',
        'wizard_id',
        string='Centros de Trabajo (Legacy)'
    )
    
    # Líneas de operaciones individuales
    operation_line_ids = fields.One2many(
        'mrp.production.wizard.operation',
        'wizard_id',
        string='Operaciones'
    )
    
    # Líneas de materiales agrupados por categoría
    material_line_ids = fields.One2many(
        'mrp.production.wizard.material',
        'wizard_id',
        string='Materiales por Categoría'
    )

    @api.depends('sale_order_id')
    def _compute_fecha_entrega(self):
        for wizard in self:
            wizard.fecha_entrega = wizard.sale_order_id.validity_date if wizard.sale_order_id else False

    @api.depends('material_line_ids.product_id', 'material_line_ids.product_qty')
    def _compute_material_cost_total(self):
        for wizard in self:
            total_cost = 0.0
            for material in wizard.material_line_ids:
                if material.product_id and material.product_qty:
                    # Obtener el costo estándar del producto
                    cost = material.product_id.standard_price or 0.0
                    total_cost += cost * material.product_qty
            wizard.material_cost_total = total_cost

    @api.depends('budget_amount', 'material_cost_total')
    def _compute_budget_status(self):
        for wizard in self:
            if wizard.budget_amount <= 0:
                wizard.budget_status = 'ok'
                wizard.budget_exceeded_percent = 0.0
            else:
                if wizard.material_cost_total <= wizard.budget_amount:
                    wizard.budget_status = 'ok'
                    wizard.budget_exceeded_percent = 0.0
                else:
                    exceeded_amount = wizard.material_cost_total - wizard.budget_amount
                    exceeded_percent = (exceeded_amount / wizard.budget_amount) * 100
                    wizard.budget_exceeded_percent = exceeded_percent
                    
                    # Si excede hasta 50%, es aceptable (warning)
                    if exceeded_percent <= 50.0:
                        wizard.budget_status = 'warning'
                    else:
                        wizard.budget_status = 'error'

    def action_create_production(self):
        self.ensure_one()
        
        # Mostrar advertencias de presupuesto sin bloquear
        if self.budget_amount > 0:
            if self.budget_status == 'warning':
                self.env.user.notify_warning(
                    'Presupuesto Excedido',
                    f'El costo de materiales (%.2f) excede el presupuesto (%.2f) en %.1f%%, pero está dentro del margen aceptable del 50%%.'
                    % (self.material_cost_total, self.budget_amount, self.budget_exceeded_percent)
                )
            elif self.budget_status == 'error':
                self.env.user.notify_warning(
                    'Presupuesto Excedido',
                    f'ADVERTENCIA: El costo de materiales (%.2f) excede el presupuesto (%.2f) en %.1f%%, más del margen aceptable del 50%%. Se continuará con la creación de la orden.'
                    % (self.material_cost_total, self.budget_amount, self.budget_exceeded_percent)
                )
        
        # Buscar la ubicación de tipo producción
        production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        if not production_location:
            raise UserError(_('No se encontró una ubicación de tipo producción en el sistema.'))
        
        # Usar la cantidad y unidad de medida del producto seleccionados en el wizard
        product_qty = self.product_qty  # Usar la cantidad definida en el wizard
        product_uom = self.product_id.uom_id.id if self.product_id else False
        
        # Crear la orden de producción usando los datos del wizard
        production = self.env['mrp.production'].create({
            'name': f"{self.sale_order_id.name} - {self.product_id.name}",
            'product_id': self.product_id.id,
            'product_qty': product_qty,
            'product_uom_id': product_uom,
            'bom_id': self.product_id.bom_ids[0].id if self.product_id.bom_ids else False,
            'origin': f"{self.sale_order_id.name} - {self.sale_order_id.client_order_ref or ''}",
            'date_start': self.start_date,
            'date_finished': self.fecha_entrega,
            'company_id': self.sale_order_id.company_id.id,
            'sale_order_id': self.sale_order_id.id,  # Asignar explícitamente la venta
        })
        
        # Refrescar el registro para asegurar que los campos computed se calculen
        production.invalidate_recordset(['sale_order_line_ids', 'order_detail_line_ids', 
                                        'order_model_line_ids', 'technical_info_ids'])
        production._compute_sale_order_line_ids()
        
        # Eliminar los movimientos de componentes generados automáticamente por el BOM
        production.move_raw_ids.unlink()
        
        # Crear las órdenes de trabajo según las operaciones del wizard
        for operation in self.operation_line_ids:
            self.env['mrp.workorder'].create({
                'name': operation.name or f"Trabajo {operation.workcenter_id.name} - {self.product_id.name} - {production.name}",
                'production_id': production.id,
                'workcenter_id': operation.workcenter_id.id,
                'operation_id': operation.operation_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': product_uom,
                'qty_producing': product_qty,  # Usar la cantidad definida en el wizard
                'duration_expected': operation.duration,
                'date_start': operation.date_start,
                'date_finished': operation.date_finished,
            })
        
        # Crear los movimientos de stock según los materiales del wizard
        for material in self.material_line_ids:
            self.env['stock.move'].create({
                'name': f"Material: {material.product_id.name}",
                'product_id': material.product_id.id,
                'product_uom_qty': material.product_qty,
                'product_uom': material.product_uom_id.id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': production_location.id,
                'production_id': production.id,
                'raw_material_production_id': production.id,
                'company_id': self.sale_order_id.company_id.id,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_id': production.id,
            'target': 'current',
        }

class MrpProductionWizardOperation(models.TransientModel):
    _name = 'mrp.production.wizard.operation'
    _description = 'Operaciones del wizard de producción'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('mrp.production.wizard', string='Wizard', required=True, ondelete='cascade')
    name = fields.Char(string='Nombre', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de Trabajo', required=True)
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operación', required=True)
    duration = fields.Float(string='Duración (minutos)', required=True)
    sequence = fields.Integer(string='Secuencia', required=True)
    date_start = fields.Datetime(string='Fecha de Inicio', required=True)
    date_finished = fields.Datetime(string='Fecha de Fin', required=True)

    _sql_constraints = [
        ('operation_workcenter_uniq', 'unique(wizard_id, operation_id, workcenter_id)',
         'No puede haber operaciones duplicadas con el mismo centro de trabajo en el mismo wizard.')
    ]

class MrpProductionWizardMaterial(models.TransientModel):
    _name = 'mrp.production.wizard.material'
    _description = 'Materiales del wizard de producción'

    wizard_id = fields.Many2one('mrp.production.wizard', string='Wizard', required=True, ondelete='cascade')
    category_id = fields.Many2one('product.category', string='Categoría')
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    product_qty = fields.Float(string='Cantidad', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unidad de Medida', required=True)
    
    # Campos de costo
    unit_cost = fields.Float(string='Costo Unitario', compute='_compute_costs', store=False)
    total_cost = fields.Float(string='Costo Total', compute='_compute_costs', store=False)
    
    @api.depends('product_id', 'product_qty')
    def _compute_costs(self):
        for rec in self:
            if rec.product_id:
                rec.unit_cost = rec.product_id.standard_price or 0.0
                rec.total_cost = rec.unit_cost * rec.product_qty
            else:
                rec.unit_cost = 0.0
                rec.total_cost = 0.0

    @api.depends('wizard_id.product_id')
    def _compute_category_id(self):
        for rec in self:
            rec.category_id = rec.wizard_id.product_id.categ_id 