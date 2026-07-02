from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    group_category_id = fields.Many2one('mrp.group.by.category', string='Agrupación por Categoría')
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta')
    product_summary = fields.Text(string='Resumen de Productos', compute='_compute_product_summary')

    @api.depends('sale_order_id', 'sale_order_id.order_line')
    def _compute_product_summary(self):
        for production in self:
            if production.sale_order_id:
                summary_dict = {}
                for line in production.sale_order_id.order_line:
                    product = line.product_id
                    if product.type in ['product', 'consu']:
                        key = product.id
                        if key not in summary_dict:
                            summary_dict[key] = {
                                'name': product.display_name,
                                'qty': 0.0,
                                'uom': line.product_uom.name
                            }
                        summary_dict[key]['qty'] += line.product_uom_qty
                # Ordenar alfabéticamente por nombre de producto
                summary_lines = [f"{v['name']}: {v['qty']} {v['uom']}" for v in sorted(summary_dict.values(), key=lambda x: x['name'])]
                production.product_summary = '\n'.join(summary_lines)
            else:
                production.product_summary = False

    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        for production in self:
            if production.origin and '-' in production.origin:
                sale_name, category_name = production.origin.split('-', 1)
                sale_order = self.env['sale.order'].search([('name', '=', sale_name)], limit=1)
                if sale_order:
                    # Agrupar líneas por producto
                    product_lines = {}
                    for line in sale_order.order_line:
                        if line.product_id.categ_id.name == category_name:
                            if line.product_id not in product_lines:
                                product_lines[line.product_id] = []
                            product_lines[line.product_id].append(line)

                    # Procesar cada producto
                    for product, lines in product_lines.items():
                        total_qty = sum(line.product_uom_qty for line in lines)
                        if product.categ_id.default_workcenter_ids:
                            for workcenter in product.categ_id.default_workcenter_ids:
                                duration = workcenter.time_efficiency or 60
                                
                                # Buscar trabajo existente para este producto y centro de trabajo
                                existing_workorder = self.env['mrp.workorder'].search([
                                    ('production_id', '=', production.id),
                                    ('workcenter_id', '=', workcenter.id),
                                    ('product_id', '=', product.id)
                                ], limit=1)

                                if existing_workorder:
                                    # Actualizar cantidad y duración del trabajo existente
                                    existing_workorder.write({
                                        'qty_producing': existing_workorder.qty_producing + total_qty,
                                        'duration': existing_workorder.duration + duration,
                                        'duration_expected': existing_workorder.duration_expected + duration
                                    })
                                else:
                                    # Crear nuevo trabajo con nombre único
                                    workorder_name = f"Trabajo {workcenter.name} - {product.name} - {production.name}"
                                    self.env['mrp.workorder'].create({
                                        'name': workorder_name,
                                        'production_id': production.id,
                                        'workcenter_id': workcenter.id,
                                        'product_id': product.id,
                                        'product_uom_id': lines[0].product_uom.id,
                                        'duration': duration,
                                        'duration_expected': duration,
                                        'qty_producing': total_qty,
                                        'state': 'pending',
                                    })
        return res

class MrpGroupByCategory(models.Model):
    _name = 'mrp.group.by.category'
    _description = 'Orden de Producción por Categoría'

    name = fields.Char(string='Referencia', required=True, default=lambda self: _('Nueva'))
    category_id = fields.Many2one('product.category', string='Categoría de Producto', required=True)
    product_ids = fields.Many2many('product.product', string='Productos', compute='_compute_products', store=True)
    bom_lines = fields.One2many('mrp.group.by.category.bom.line', 'group_id', string='Componentes Agrupados')
    workorder_lines = fields.One2many('mrp.group.by.category.workorder.line', 'group_id', string='Tareas Agrupadas')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Hecho')
    ], default='draft', string='Estado')
    production_id = fields.Many2one('mrp.production', string='Orden de Producción Generada')
    production_workorder_id = fields.Many2one('mrp.production', string='Orden de Producción de Trabajo')
    product_qty = fields.Float(string='Cantidad Total', default=1.0)
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta')
    product_id = fields.Many2one('product.product', string='Producto a Producir', domain="[('categ_id', '=', category_id)]", required=True)
    
    # Campos para la vista kanban
    pending_tasks_count = fields.Integer(string='Tareas Pendientes', compute='_compute_pending_tasks')
    completed_tasks_count = fields.Integer(string='Tareas Completadas', compute='_compute_pending_tasks')
    total_tasks_count = fields.Integer(string='Total Tareas', compute='_compute_pending_tasks')
    progress = fields.Float(string='Progreso', compute='_compute_pending_tasks')
    color = fields.Integer(string='Color Index', default=0)
    
    @api.depends('workorder_lines.state')
    def _compute_pending_tasks(self):
        for rec in self:
            if rec.workorder_lines:
                rec.pending_tasks_count = len(rec.workorder_lines.filtered(lambda w: w.state == 'pending'))
                rec.completed_tasks_count = len(rec.workorder_lines.filtered(lambda w: w.state == 'done'))
                rec.total_tasks_count = len(rec.workorder_lines)
                rec.progress = (rec.completed_tasks_count / rec.total_tasks_count) * 100 if rec.total_tasks_count > 0 else 0
            else:
                rec.pending_tasks_count = 0
                rec.completed_tasks_count = 0
                rec.total_tasks_count = 0
                rec.progress = 0

    @api.depends('category_id')
    def _compute_products(self):
        for rec in self:
            if rec.category_id:
                rec.product_ids = self.env['product.product'].search([
                    ('categ_id', '=', rec.category_id.id),
                    ('type', 'in', ['product', 'consu'])
                ])
            else:
                rec.product_ids = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            if self.category_id.default_product_id:
                self.product_id = self.category_id.default_product_id
            else:
                self.product_id = False
        else:
            self.product_id = False

    def action_generate_grouped_production(self):
        for rec in self:
            if not rec.product_id:
                raise UserError(_('Debe seleccionar el producto a producir antes de generar la orden de producción.'))
            
            if not rec.category_id.production_product_id:
                raise UserError(_('Debe configurar el Producto General de Producción en la categoría antes de continuar.'))
            
            bom_lines = {}
            workorder_lines = {}
            
            # Verificar si ya existe una orden de producción de trabajo para esta orden de venta
            existing_workorder = self.env['mrp.production'].search([
                ('origin', '=', f"{rec.sale_order_id.name}-Trabajo"),
                ('state', '!=', 'cancel')
            ], limit=1)

            # Verificar si ya existe una orden de producción de materiales para esta orden de venta y categoría
            existing_material = self.env['mrp.production'].search([
                ('origin', '=', f"{rec.sale_order_id.name}-{rec.category_id.name}-Materiales"),
                ('state', '!=', 'cancel')
            ], limit=1)

            # Recorrer cada línea de la orden de venta
            if rec.sale_order_id:
                for line in rec.sale_order_id.order_line:
                    product = line.product_id
                    # Solo procesar productos de la categoría actual
                    if product.categ_id != rec.category_id:
                        continue
                    qty = line.product_uom_qty
                    bom = self.env['mrp.bom'].sudo().search([
                        ('product_tmpl_id', '=', product.product_tmpl_id.id),
                        ('company_id', '=', self.env.company.id),
                        ('type', '=', 'normal'),
                    ], limit=1)
                    if not bom or not isinstance(bom, models.Model) or not bom.exists() or not hasattr(bom, 'bom_line_ids'):
                        continue
                    # Calcular el factor basado en la cantidad de la línea
                    factor = qty / bom.product_qty if bom.product_qty else qty
                    for bom_line in bom.bom_line_ids:
                        # Check for fabric component and apply category's fabric color
                        component_product = bom_line.product_id
                        if rec.category_id.fabric_color_id and 'Color' in component_product.attribute_line_ids.mapped('attribute_id.name') and 'Tela' in component_product.name:
                            # Find the product variant with the specified fabric color
                            color_attribute = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
                            if color_attribute:
                                product_with_color = self.env['product.product'].search([
                                    ('product_tmpl_id', '=', component_product.product_tmpl_id.id),
                                    ('attribute_value_ids', 'in', rec.category_id.fabric_color_id.id)
                                ], limit=1)
                                if product_with_color:
                                    component_product = product_with_color

                        key = component_product.id
                        if key not in bom_lines:
                            bom_lines[key] = {
                                'product_id': component_product.id,
                                'product_uom_id': bom_line.product_uom_id.id,
                                'product_qty': 0.0,
                            }
                        product_qty = bom_line.product_qty * factor
                        if bom_line.product_uom_id != bom_line.product_id.uom_id:
                            product_qty = self.env['uom.uom']._compute_quantity(
                                product_qty,
                                bom_line.product_id.uom_id,
                                bom_line.product_uom_id
                            )
                        bom_lines[key]['product_qty'] += product_qty
                    # Sumar operaciones/tareas
                    if hasattr(bom, 'operation_ids'):
                        for op in bom.operation_ids:
                            key = op.name
                            if key not in workorder_lines:
                                workorder_lines[key] = {
                                    'operation_id': op.id,
                                    'name': op.name,
                                    'workcenter_id': op.workcenter_id.id,
                                    'time_cycle': 0.0,
                                    'sequence': op.sequence,
                                }
                            workorder_lines[key]['time_cycle'] += op.time_cycle * factor

            # Limpiar líneas previas
            rec.bom_lines.unlink()
            rec.workorder_lines.unlink()
            
            # Crear líneas agrupadas
            for vals in bom_lines.values():
                self.env['mrp.group.by.category.bom.line'].create({
                    'group_id': rec.id,
                    **vals
                })
            
            for vals in workorder_lines.values():
                self.env['mrp.group.by.category.workorder.line'].create({
                    'group_id': rec.id,
                    'operation_id': vals['operation_id'],
                    'name': vals['name'],
                    'workcenter_id': vals['workcenter_id'],
                    'time_cycle': vals['time_cycle'],
                    'sequence': vals['sequence'],
                })

            # Si existe una orden de trabajo anterior, cancelarla
            if existing_workorder:
                existing_workorder.action_cancel()

            # Crear nueva orden de producción para trabajo
            if workorder_lines:  # Solo crear si hay operaciones de trabajo
                production_workorder = self.env['mrp.production'].create({
                    'product_id': rec.category_id.production_product_id.id,
                    'product_qty': rec.product_qty,
                    'product_uom_id': rec.category_id.production_product_id.uom_id.id,
                    'bom_id': False,
                    'origin': f"{rec.sale_order_id.name}-Trabajo",
                    'state': 'confirmed',
                    'group_category_id': rec.id,
                    'sale_order_id': rec.sale_order_id.id,  # Relacionar con la orden de venta
                    'workorder_ids': [(0, 0, {
                        'name': w['name'],
                        'workcenter_id': w['workcenter_id'],
                        'duration_expected': w['time_cycle'],
                        'sequence': w['sequence'],
                        'product_uom_id': rec.category_id.production_product_id.uom_id.id,
                    }) for w in workorder_lines.values()]
                })
                rec.production_workorder_id = production_workorder.id

            # Si existe una orden de materiales anterior, cancelarla
            if existing_material:
                existing_material.action_cancel()

            # Crear nueva orden de producción para materiales
            production = self.env['mrp.production'].create({
                'product_id': rec.product_id.id,
                'product_qty': rec.product_qty,
                'product_uom_id': rec.product_id.uom_id.id,
                'bom_id': False,
                'origin': f"{rec.sale_order_id.name}-{rec.category_id.name}-Materiales",
                'state': 'confirmed',
                'group_category_id': rec.id,
                'sale_order_id': rec.sale_order_id.id,  # Relacionar con la orden de venta
                'move_raw_ids': [(0, 0, {
                    'product_id': l['product_id'],
                    'product_uom_qty': l['product_qty'],
                    'product_uom': l['product_uom_id'],
                    'name': _('Consumo de %s') % self.env['product.product'].browse(l['product_id']).name,
                }) for l in bom_lines.values()],
            })
            rec.production_id = production.id
            rec.state = 'confirmed'

class MrpGroupByCategoryBomLine(models.Model):
    _name = 'mrp.group.by.category.bom.line'
    _description = 'Línea de Componente Agrupado'

    group_id = fields.Many2one('mrp.group.by.category', string='Agrupación', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Componente', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unidad de Medida', required=True)
    product_qty = fields.Float(string='Cantidad', required=True)

class MrpGroupByCategoryWorkorderLine(models.Model):
    _name = 'mrp.group.by.category.workorder.line'
    _description = 'Línea de Tarea Agrupada'

    group_id = fields.Many2one('mrp.group.by.category', string='Agrupación', ondelete='cascade')
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operación/Tarea', required=True)
    name = fields.Char(string='Nombre', related='operation_id.name', store=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de Trabajo', related='operation_id.workcenter_id', store=True)
    time_cycle = fields.Float(string='Tiempo de Ciclo', related='operation_id.time_cycle', store=True)
    sequence = fields.Integer(string='Secuencia', related='operation_id.sequence', store=True)
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta', related='group_id.sale_order_id', store=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('done', 'Hecho')
    ], string='Estado', default='pending')
    
    # New fields for Kanban view
    date_start = fields.Datetime(string='Fecha de Inicio Prevista')
    date_end = fields.Datetime(string='Fecha de Fin Prevista')
    # Campo related para el resumen de productos
    product_summary = fields.Text(string='Resumen de productos', related='group_id.production_workorder_id.product_summary', store=False, readonly=True)
    
    def action_start(self):
        self.write({'state': 'in_progress'})
        
    def action_done(self):
        self.write({'state': 'done'})
        
    def action_reset(self):
        self.write({'state': 'pending'})

