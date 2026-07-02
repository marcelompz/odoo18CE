# -*- coding: utf-8 -*-
"""
Created on 2025-03-26 09:19:44

@author: drojo
"""
# python
import logging
from collections import defaultdict

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class StockLandedCostInherit(models.Model):
    _inherit = 'stock.landed.cost'

    @api.model_create_multi
    def create(self, vals_list):
        products = self.env['product.product'].search([('landed_cost_ok', '=', True)])

        for values in vals_list:
            # Obtener la factura si existe
            bill_id = values.get('vendor_bill_id')
            bill = self.env['account.move'].browse(bill_id) if bill_id else False

            # Obtener recepciones asociadas en estado 'done' (más eficiente con filtered_domain)
            pickings = bill.line_ids.mapped('purchase_line_id.order_id.picking_ids') if bill else []
            pickings = pickings.filtered_domain([('state', '=', 'done')]) if pickings else []

            # Construcción de líneas de costos
            cost_lines = []
            for product in products:
                product_tmpl = product.product_tmpl_id
                accounts = product_tmpl.get_product_accounts()
                
                cost_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': product.name,
                    'split_method': product_tmpl.split_method_landed_cost or product.split_method_landed_cost or 'equal',
                    'price_unit': (abs(bill.amount_total_signed) * (product.landed_cost_percentage or 0.0)) if bill else 0.0,
                    'account_id': accounts.get('stock_input', False) and accounts['stock_input'].id,
                    'product_landed_cost_percentage': product.landed_cost_percentage,
                }))

            # Actualizar valores antes de la creación
            values.update({
                'cost_lines': cost_lines,
                'picking_ids': [(6, 0, pickings.ids)] if pickings else [],
            })

        # Crear los registros en batch
        return super().create(vals_list)

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Las líneas de costo y ajuste no coinciden. Quizás debería recalcular los costos de entrega.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            cost_to_add_bylot = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id._get_stock_valuation_layer_ids().mapped('remaining_qty'))
                linked_layer = line.move_id._get_stock_valuation_layer_ids()

                # Prorate the value at what's still in stock
                move_qty = line.move_id.product_uom._compute_quantity(line.move_id.quantity, line.move_id.product_id.uom_id)
                cost_to_add = (remaining_qty / move_qty) * line.additional_landed_cost
                product = line.move_id.product_id
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    vals_list = []
                    if line.move_id.product_id.lot_valuated:
                        for lot_id, sml in line.move_id.move_line_ids.grouped('lot_id').items():
                            lot_layer = linked_layer.filtered(lambda l: l.lot_id == lot_id)[:1]
                            value = cost_to_add * sum(sml.mapped('quantity')) / line.move_id.quantity
                            if product.cost_method in ['average', 'fifo']:
                                cost_to_add_bylot[lot_id] += value
                            vals_list.append({
                                'value': value,
                                'unit_cost': 0,
                                'quantity': 0,
                                'remaining_qty': 0,
                                'stock_valuation_layer_id': lot_layer.id,
                                'description': cost.name,
                                'stock_move_id': line.move_id.id,
                                'product_id': line.move_id.product_id.id,
                                'stock_landed_cost_id': cost.id,
                                'company_id': cost.company_id.id,
                                'lot_id': lot_id.id,
                            })
                            lot_layer.remaining_value += value
                    else:
                        vals_list.append({
                            'value': cost_to_add,
                            'unit_cost': 0,
                            'quantity': 0,
                            'remaining_qty': 0,
                            'stock_valuation_layer_id': linked_layer[:1].id,
                            'description': cost.name,
                            'stock_move_id': line.move_id.id,
                            'product_id': line.move_id.product_id.id,
                            'stock_landed_cost_id': cost.id,
                            'company_id': cost.company_id.id,
                        })
                        linked_layer[:1].remaining_value += cost_to_add
                    valuation_layer = self.env['stock.valuation.layer'].create(vals_list)
                    valuation_layer_ids += valuation_layer.ids
                # Update the AVCO/FIFO
                if product.cost_method in ['average', 'fifo']:
                    cost_to_add_byproduct[product] += cost_to_add
                # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.quantity - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.quantity
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            # batch standard price computation avoid recompute quantity_svl at each iteration
            products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys()).with_company(cost.company_id)
            for product in products:  # iterate on recordset to prefetch efficiently quantity_svl
                if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.sudo().with_context(disable_auto_svl=True).standard_price += cost_to_add_byproduct[product] / product.quantity_svl
                if product.lot_valuated:
                    for lot, value in cost_to_add_bylot.items():
                        if float_is_zero(lot.quantity_svl, precision_rounding=product.uom_id.rounding):
                            continue
                        lot.sudo().with_context(disable_auto_svl=True).standard_price += value / lot.quantity_svl

                # Releer el precio de costo después de la actualización para asegurarse de que tiene el valor correcto
                product.sudo().read(['standard_price'])

                # Obtener el margen de ganancia
                margin_gain = (
                    product.product_tmpl_id.margin_gain
                    if product.product_tmpl_id.margin_gain > 0
                    else product.product_tmpl_id.categ_id.margin_gain
                )

                # Calcular el nuevo precio de venta basado en el precio de costo actualizado
                if margin_gain > 0:
                    new_sale_price = product.standard_price * (1 + margin_gain)                    
                    product.sudo().write({'list_price': new_sale_price})

            move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            # We will only create the accounting entry when there are defined lines (the lines will be those linked to products of real_time valuation category).
            cost_vals = {'state': 'done'}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({'account_move_id': move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()
            cost.reconcile_landed_cost()
        return True

class StockLandedCostLinesInherit(models.Model):
    _inherit = 'stock.landed.cost.lines'

    product_landed_cost_percentage = fields.Float(
        string='%', help='Costo porcentaje de la factura')
    product_price_real = fields.Monetary(
        string='Precio real', currency_field='currency_id')
    bill_reference = fields.Char(
        string='Referencia', help='Referencia o número de factura de compra')
    supplier_id = fields.Many2one(
        'res.partner', string='Proveedor', domain='[("supplier_rank","!=",0)]')
    state = fields.Selection(
        related='cost_id.state')
    move_id = fields.Many2one(
        'account.move', string='Factura')

    # Campos transitorios para controlar el flujo de los onchanges
    _ignore_price_unit_onchange = fields.Boolean(
        store=False, # Importante: no se guarda en la base de datos
        help="Flag para ignorar el onchange de price_unit temporalmente."
    )
    _ignore_percentage_onchange = fields.Boolean(
        store=False,
        help="Flag para ignorar el onchange de product_landed_cost_percentage temporalmente."
    )

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        # Si este onchange fue disparado por el onchange del porcentaje, lo ignoramos.
        if self._ignore_price_unit_onchange:
            self._ignore_price_unit_onchange = False # Resetear la bandera
            return

        self.product_price_real = self.price_unit

        # Si hay un producto y un costo de desembarque válido
        if self.product_id and self.cost_id and self.cost_id.vendor_bill_id and self.price_unit:
            # Establecer la bandera para que onchange_product_landed_cost_percentage no se dispare recursivamente
            self._ignore_percentage_onchange = True
            # Calcular el porcentaje basado en el precio unitario actual
            # Asegúrate de que amount_total_signed no sea cero para evitar división por cero
            if self.price_unit != 0:
                self.product_landed_cost_percentage = abs(self.price_unit / self.cost_id.vendor_bill_id.amount_total_signed)
            else:
                self.product_landed_cost_percentage = 0.0
        else:
            self.product_landed_cost_percentage = 0.0 # O el valor inicial que desees

    @api.onchange('product_landed_cost_percentage')
    def _onchange_product_landed_cost_percentage(self):
        """Actualizar precio unitario basado en el porcentaje de costo de producto"""
        # Si este onchange fue disparado por el onchange de price_unit, lo ignoramos.
        if self._ignore_percentage_onchange:
            self._ignore_percentage_onchange = False # Resetear la bandera
            return

        # Si hay un costo de desembarque válido y un porcentaje
        if self.cost_id and self.cost_id.vendor_bill_id and self.product_landed_cost_percentage:
            # Establecer la bandera para que onchange_price_unit no se dispare recursivamente
            self._ignore_price_unit_onchange = True
            # Calcular price_unit basado en el porcentaje
            self.price_unit = abs(self.cost_id.vendor_bill_id.amount_total_signed * self.product_landed_cost_percentage)
        else:
            self.price_unit = 0.0

        self.product_price_real = self.price_unit

    @api.onchange('product_id')
    def onchange_product_id(self):
        """Actualizar porcentaje de costo basado en el producto seleccionado"""
        if self.product_id:
            self.product_landed_cost_percentage = self.product_id.landed_cost_percentage
        return super().onchange_product_id()

    def action_create_bill(self):
        """
        Genera una factura de compra en estado borrador
        """
        if self.product_price_real <= 0 or not self.supplier_id:
            raise UserError('Los campos Precio real y Proveedor son obligatorios')

        # Validar que el porcentaje de costo del producto es correcto
        if self.product_landed_cost_percentage <= 0:
            raise UserError('El porcentaje de costo debe ser mayor que cero.')

        try:
            # Construcción de las líneas de la factura
            invoice_lines = [(0, 0, {
                'product_id': self.product_id.id,
                'name': self.product_id.name,
                'price_unit': self.product_price_real,
                'quantity': 1,
                'tax_ids': [(6, 0, self.product_id.supplier_taxes_id.ids)],
            })]

            # Crear la factura de compra
            invoice = self.env['account.move'].create({
                'ref': self.bill_reference,
                'move_type': 'in_invoice',
                'invoice_origin': self.cost_id.name,
                'invoice_user_id': self.env.user.id,
                'partner_id': self.supplier_id.id,
                'currency_id': self.cost_id.currency_id.id,
                'invoice_line_ids': invoice_lines,
            })

            if invoice:
                self.move_id = invoice.id

                # Acción para abrir la factura en el formulario
                result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
                result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
                result['res_id'] = invoice.id

                return result

        except UserError as e:
            raise e  # Mantener la excepción específica
        except Exception as e:
            # Manejo de cualquier otra excepción
            raise UserError(_('No se pudo crear la factura: %s' % str(e)))
