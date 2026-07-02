from odoo import models, fields, api, _
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_id = fields.Many2one(
        'sale.order', string='Orden de Venta',
        readonly=True,
        states={'draft': [('readonly', False)]})

    sale_order_line_ids = fields.Many2many(
        comodel_name='sale.order.line',
        string='Líneas de Pedido',
        compute='_compute_sale_order_line_ids',
        store=False
    )
    order_detail_line_ids = fields.Many2many(
        comodel_name='order.detail.lines',
        string='Líneas de Detalle',
        compute='_compute_sale_order_line_ids',
        store=False
    )
    order_model_line_ids = fields.Many2many(
        comodel_name='order.detail.model.lines',
        string='Líneas de Modelos',
        compute='_compute_sale_order_line_ids',
        store=False
    )
    technical_info_ids = fields.Many2many(
        comodel_name='sale.order.technical.info',
        string='Información Técnica',
        compute='_compute_sale_order_line_ids',
        store=False
    )
    sale_order_line_summary_ids = fields.One2many(
        comodel_name='mrp.production.sale.line.summary',
        inverse_name='production_id',
        string='Resumen de Productos',
        compute='_compute_sale_order_line_summary_ids',
        store=False
    )
    sale_order_line_summary_html = fields.Html(
        string='Resumen de Productos',
        compute='_compute_sale_order_line_summary_html',
        store=False
    )
    category_summary_ids = fields.One2many(
        comodel_name='mrp.production.category.summary',
        inverse_name='production_id',
        string='Resumen por Categoría',
        compute='_compute_category_summary_ids',
        store=False
    )
    product_categ_id = fields.Many2one(
        related='product_id.categ_id',
        string='Categoría del Producto',
        store=True,
        readonly=True
    )
    workorders_summary_html = fields.Html(
        string='Resumen de trabajos',
        compute='_compute_workorders_summary_html',
        store=False
    )
    workorders_summary_json = fields.Json(
        string='Resumen de trabajos (json)',
        compute='_compute_workorders_summary_json',
        store=False
    )

    @api.depends('origin', 'sale_order_id')
    def _compute_sale_order_line_ids(self):
        for production in self:
            sale_order = False
            # Primero intentar usar el campo sale_order_id directamente
            if production.sale_order_id:
                sale_order = production.sale_order_id
            # Si no está disponible, intentar obtenerlo desde origin
            elif production.origin:
                # Intentar diferentes formatos de origin
                sale_order_name = None
                if ' - ' in production.origin:
                    # Formato: "SO001 - Referencia Cliente"
                    sale_order_name = production.origin.split(' - ')[0].strip()
                elif '-' in production.origin:
                    # Formato: "SO001-Referencia" o "123-SO001"
                    parts = production.origin.split('-')
                    for part in parts:
                        part = part.strip()
                        # Intentar encontrar un nombre de orden de venta (empieza con SO)
                        if part.startswith('SO') or part.startswith('S'):
                            sale_order_name = part
                            break
                        # O intentar como ID numérico
                        try:
                            sale_order_id = int(part)
                            sale_order = self.env['sale.order'].browse(sale_order_id)
                            if sale_order.exists():
                                break
                        except (ValueError, TypeError):
                            continue
                
                if sale_order_name and not sale_order:
                    sale_order = self.env['sale.order'].search([('name', '=', sale_order_name)], limit=1)
            
            if sale_order:
                production.sale_order_line_ids = sale_order.order_line.ids
                production.order_detail_line_ids = sale_order.order_detail_lines.ids
                production.order_model_line_ids = sale_order.model_line_ids.ids
                production.technical_info_ids = sale_order.technical_info_ids.ids
            else:
                production.sale_order_line_ids = [(5, 0, 0)]
                production.order_detail_line_ids = [(5, 0, 0)]
                production.order_model_line_ids = [(5, 0, 0)]
                production.technical_info_ids = [(5, 0, 0)]

    @api.model
    def create(self, vals):
        # Asegurar que el nombre sea único por compañía
        if 'name' in vals:
            company_id = vals.get('company_id', self.env.company.id)
            base_name = vals['name']
            counter = 1
            while True:
                # Buscar si ya existe una orden con el mismo nombre en la misma compañía
                existing = self.search([
                    ('name', '=', vals['name']),
                    ('company_id', '=', company_id)
                ])
                if not existing:
                    break
                vals['name'] = f"{base_name} ({counter})"
                counter += 1
        
        production = super(MrpProduction, self).create(vals)
        
        # Si se proporciona sale_order_id, asegurar que los datos se copien
        if 'sale_order_id' in vals and vals.get('sale_order_id'):
            sale_order = self.env['sale.order'].browse(vals['sale_order_id'])
            if sale_order.exists():
                # Forzar el cálculo de los campos computed
                production._compute_sale_order_line_ids()
        
        return production

    def write(self, vals):
        # Asegurar que el nombre sea único por compañía al actualizar
        if 'name' in vals:
            for record in self:
                base_name = vals['name']
                counter = 1
                while True:
                    # Buscar si ya existe una orden con el mismo nombre en la misma compañía
                    existing = self.search([
                        ('name', '=', vals['name']),
                        ('company_id', '=', record.company_id.id),
                        ('id', '!=', record.id)
                    ])
                    if not existing:
                        break
                    vals['name'] = f"{base_name} ({counter})"
                    counter += 1
        return super(MrpProduction, self).write(vals)

    @api.onchange('origin')
    def _onchange_origin(self):
        if self.origin:
            sale_name = None
            if ' - ' in self.origin:
                sale_name = self.origin.split(' - ')[0].strip()
            elif '-' in self.origin:
                parts = self.origin.split('-')
                for part in parts:
                    part = part.strip()
                    if part.startswith('SO') or part.startswith('S'):
                        sale_name = part
                        break
            
            if sale_name:
                sale_order = self.env['sale.order'].search([('name', '=', sale_name)], limit=1)
                if sale_order:
                    self.sale_order_id = sale_order.id
                    if sale_order.validity_date:
                        self.date_finished = fields.Datetime.from_string(sale_order.validity_date)
                    # Forzar el cálculo de los campos computed
                    self._compute_sale_order_line_ids()
                else:
                    self.sale_order_id = False
            else:
                self.sale_order_id = False
    
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Actualizar datos cuando cambia la orden de venta"""
        if self.sale_order_id:
            if self.sale_order_id.validity_date:
                self.date_finished = fields.Datetime.from_string(self.sale_order_id.validity_date)
            # Forzar el cálculo de los campos computed
            self._compute_sale_order_line_ids()

    def _compute_sale_order_line_summary_ids(self):
        for production in self:
            summary_lines = []
            product_qty_map = defaultdict(float)
            sale_order = production.sale_order_id  # Usar el campo relacionado correcto
            if sale_order:
                for line in sale_order.order_line:
                    product_qty_map[line.product_id] += line.product_uom_qty
                # Ordenar por nombre de producto
                for product in sorted(product_qty_map, key=lambda p: p.name):
                    summary_lines.append((0, 0, {
                        'product_id': product.id,
                        'product_qty': product_qty_map[product],
                    }))
            production.sale_order_line_summary_ids = summary_lines

    def _compute_sale_order_line_summary_html(self):
        for production in self:
            summary = {}
            sale_order = production.sale_order_id  # Usar el campo relacionado correcto
            if sale_order:
                for line in sale_order.order_line:
                    key = line.product_id
                    summary.setdefault(key, 0)
                    summary[key] += line.product_uom_qty
            html = "<table class='table table-sm'><tr><th>Producto</th><th>Cantidad Total</th></tr>"
            for product in sorted(summary, key=lambda p: p.name):
                html += f"<tr><td>{product.display_name}</td><td>{summary[product]}</td></tr>"
            html += "</table>" if summary else "<i>No hay productos en el pedido</i>"
            production.sale_order_line_summary_html = html

    def _compute_category_summary_ids(self):
        for production in self:
            summary_lines = []
            category_qty_map = defaultdict(float)
            sale_order = production.sale_order_id
            if sale_order:
                for line in sale_order.order_line:
                    category = line.product_id.categ_id
                    category_qty_map[category] += line.product_uom_qty
                for category in sorted(category_qty_map, key=lambda c: c.name if c else ''):
                    summary_lines.append((0, 0, {
                        'category_id': category.id if category else False,
                        'product_qty': category_qty_map[category],
                    }))
            production.category_summary_ids = summary_lines

    @api.depends('workorder_ids')
    def _compute_workorders_summary_html(self):
        for rec in self:
            html = ''
            for wo in rec.workorder_ids:
                estado = dict(wo._fields['state'].selection).get(wo.state, wo.state)
                html += f"<b>Trabajo:</b> {wo.name} <b>Centro:</b> {wo.workcenter_id.display_name} <b>Estado:</b> {estado}<br/>"
            rec.workorders_summary_html = html

    @api.depends('workorder_ids')
    def _compute_workorders_summary_json(self):
        for rec in self:
            _logger.info(f'PRODUCCION {rec.id} - workorder_ids: {rec.workorder_ids.ids}')
            resumen = []
            for wo in rec.workorder_ids:
                estado = dict(wo._fields['state'].selection).get(wo.state, wo.state)
                resumen.append({
                    'id': wo.id,
                    'name': wo.name,
                    'workcenter': wo.workcenter_id.display_name,
                    'state': estado
                })
            rec.workorders_summary_json = resumen

class MrpProductionSaleLineSummary(models.TransientModel):
    _name = 'mrp.production.sale.line.summary'
    _description = 'Resumen de Productos de Pedido de Venta para Fabricación'

    production_id = fields.Many2one('mrp.production', string='Fabricación')
    product_id = fields.Many2one('product.product', string='Producto')
    product_qty = fields.Float(string='Cantidad Total')

class MrpProductionCategorySummary(models.TransientModel):
    _name = 'mrp.production.category.summary'
    _description = 'Resumen de Categorías de Productos de Pedido de Venta para Fabricación'

    production_id = fields.Many2one('mrp.production', string='Fabricación')
    category_id = fields.Many2one('product.category', string='Categoría de Producto')
    product_qty = fields.Float(string='Cantidad Total') 