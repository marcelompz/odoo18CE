# -*- coding: utf-8 -*-
"""
Created on 2025-11-28 11:15:10

@author: drojo
"""
# python
import logging
from collections import defaultdict

# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductionWave(models.Model):
    _name = 'production.wave'
    _description = 'Ola de Producción y Abastecimiento'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Referencia', required=True, copy=False, readonly=True, default='Nuevo')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('done', 'Transferencias Generadas')
    ], string='Estado', default='draft', tracking=True)
    sale_order_ids = fields.One2many(
        'sale.order', 'production_wave_id', string='Cotizaciones Seleccionadas', domain=[('state', 'in', ['sale', 'done'])])
    product_line_ids = fields.One2many(
        'production.wave.product.line', 'wave_id', string='Resumen de Productos')
    component_line_ids = fields.One2many(
        'production.wave.component.line', 'wave_id', string='Lista de Materiales')
    picking_ids = fields.Many2many(
        'stock.picking', string='Traslados Realizados', copy=False)
    picking_count = fields.Integer(
        string='Cantidad de traslados', compute='_compute_picking_count')

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('production.wave') or 'Nuevo'
        return super().create(vals_list)

    def _explode_recursive(self, product, qty, grouped_components):
        """
        Navega recursivamente por la BoM.
        - Si tiene BoM: Explota y llama a la función para sus hijos.
        - Si NO tiene BoM: Agrega el producto a la lista de materiales requeridos.
        """
        # Buscamos BoM en el contexto de la compañía actual
        bom = self.env['mrp.bom']._bom_find(product, company_id=self.env.company.id)[product]

        if not bom:
            # CASO BASE: Es una materia prima final (o producto sin BoM)
            # Lo agregamos al diccionario de componentes
            key = product
            grouped_components[key]['qty'] += qty
            grouped_components[key]['uom'] = product.uom_id.id
            
            # Asignamos ubicaciones por defecto si aún no están seteadas para este material
            if not grouped_components[key]['src_loc']:
                # Origen: Configuración del producto o Stock por defecto
                src = product.wave_source_location_id.id or self.env.ref('stock.stock_location_stock').id
                # Destino: Configuración del producto o Stock por defecto (ajusta esto si usas Pre-Producción)
                dest = product.wave_dest_location_id.id or self.env.ref('stock.stock_location_stock').id
                
                grouped_components[key]['src_loc'] = src
                grouped_components[key]['dest_loc'] = dest
            return

        # CASO RECURSIVO: Tiene BoM -> Explotar
        boms_done, lines_done = bom.explode(product, qty)
        
        for bom_line, line_data in lines_done:
            # Llamada a sí mismo con el componente hijo y la cantidad calculada
            self._explode_recursive(
                bom_line.product_id, 
                line_data['qty'], 
                grouped_components
            )

    def action_calculate_requirements(self):
        self.ensure_one()
        if not self.sale_order_ids:
            raise UserError("Por favor selecciona al menos una cotización.")

        # Limpieza inicial
        self.write({
            'product_line_ids': [Command.clear()],
            'component_line_ids': [Command.clear()],
        })

        # Estructuras
        grouped_products = defaultdict(float)
        grouped_components = defaultdict(lambda: {
            'qty': 0.0, 
            'src_loc': False, 
            'dest_loc': False,
            'uom': False
        })

        # Paso 1: Agrupar productos de ventas
        for order in self.sale_order_ids:
            for line in order.order_line:
                if line.display_type or not line.product_id:
                    continue
                grouped_products[line.product_id] += line.product_uom_qty

        product_lines_values = []
        component_lines_values = []

        # Paso 2: Calcular (usando recursividad)
        for product, total_qty in grouped_products.items():
            # a) Llenar resumen de productos vendidos
            product_lines_values.append(Command.create({
                'product_id': product.id,
                'qty_total': total_qty,
            }))

            # b) Llenar componentes (Recursivamente)
            # Nota: Si vendes "Tela" directamente (sin BoM), la función recursiva
            # también lo manejará correctamente agregándolo a grouped_components.
            self._explode_recursive(product, total_qty, grouped_components)

        # Paso 3: Crear líneas en base de datos
        for product, data in grouped_components.items():
            # Pequeña limpieza: redondear cantidades para evitar 0.00000001
            # qty_rounded = float_round(data['qty'], precision_rounding=product.uom_id.rounding)
            
            component_lines_values.append(Command.create({
                'product_id': product.id,
                'uom_id': data['uom'] or product.uom_id.id,
                'qty_needed': data['qty'],
                'location_id': data['src_loc'],
                'location_dest_id': data['dest_loc'],
            }))

        self.write({
            'product_line_ids': product_lines_values,
            'component_line_ids': component_lines_values,
            'state': 'calculated'
        })

    def action_generate_transfers(self):
        self.ensure_one()
        stock_picking_obj = self.env['stock.picking']
        
        # Agrupar componentes por (Origen, Destino) para crear albaranes consolidados
        moves_by_route = defaultdict(list)

        for line in self.component_line_ids:
            if not line.location_id or not line.location_dest_id:
                raise UserError(_("Faltan ubicaciones para el producto %s") % line.product_id.name)
            
            if line.qty_needed <= 0:
                continue

            key = (line.location_id, line.location_dest_id)
            moves_by_route[key].append(line)

        if not moves_by_route:
            raise UserError("No hay cantidades para transferir.")

        created_pickings = self.env['stock.picking']
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        for (src, dest), lines in moves_by_route.items():
            # Crear el Picking (Cabecera)
            picking = stock_picking_obj.create({
                'picking_type_id': picking_type.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'origin': self.name,
                'company_id': self.env.company.id,
            })

            # Crear los Moves (Líneas)
            move_vals = []
            for line in lines:
                move_vals.append(Command.create({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty_needed,
                    'product_uom': line.uom_id.id,
                    'location_id': src.id,
                    'location_dest_id': dest.id,
                    'picking_id': picking.id
                }))
            
            picking.write({'move_ids_without_package': move_vals})
            created_pickings |= picking

            # Actualizar columna "Cantidad Entregada" (simulado, realmente es "Transferido")
            for line in lines:
                line.qty_delivered += line.qty_needed

        self.picking_ids = created_pickings

        self.state = 'done'
        
        # Retornar acción para ver los pickings creados
        return self.action_view_pickings()

    def action_view_pickings(self):
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        if not self.picking_ids or len(self.picking_ids) > 1:
            result['domain'] = [('id', 'in', self.picking_ids.ids)]
        
        elif len(self.picking_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = self.picking_ids.id
        
        return result


class ProductionWaveProductLine(models.Model):
    _name = 'production.wave.product.line'
    _description = 'Resumen de Productos Vendidos'

    wave_id = fields.Many2one(
        'production.wave', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Producto', required=True)
    qty_total = fields.Float(
        string='Total Vendido')
    

class ProductionWaveComponentLine(models.Model):
    _name = 'production.wave.component.line'
    _description = 'Materiales Requeridos y Ubicaciones'

    wave_id = fields.Many2one(
        'production.wave', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Producto / Material', required=True)
    uom_id = fields.Many2one(
        'uom.uom', string='UdM')
    qty_needed = fields.Float(
        string='Cant. Necesaria')
    qty_delivered = fields.Float(
        string='Cant. Entregada (Generada)', readonly=True, help="Cantidad ya enviada a pickings")
    location_id = fields.Many2one(
        'stock.location', string='Origen', domain="[('usage','=','internal')]")
    location_dest_id = fields.Many2one(
        'stock.location', string='Destino (Prod)', domain="[('usage','=','internal')]")
