# -*- coding: utf-8 -*-
"""
Created on 2025-04-22 14:41:25

@author: drojo
"""
# python
import logging
from collections import defaultdict

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class StockLandedCostInherit(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Las líneas de costo y ajuste no coinciden. Quizás debería recalcular los costos de entrega.'))

        wizard_lines_data = []
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
            products_to_update = self.env['product.product'] # Track products for the wizard
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
                # Products with manual inventory valuation are ignored.
                if product.valuation != "real_time":
                    continue
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.quantity - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.quantity
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)
                products_to_update |= product # Add product to the set

            # batch standard price computation
            products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys()).with_company(cost.company_id)
            for product in products:
                if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.sudo().with_context(disable_auto_svl=True).standard_price += cost_to_add_byproduct[product] / product.quantity_svl
                if product.lot_valuated:
                    for lot, value in cost_to_add_bylot.items():
                        if float_is_zero(lot.quantity_svl, precision_rounding=product.uom_id.rounding):
                            continue
                        lot.sudo().with_context(disable_auto_svl=True).standard_price += value / lot.quantity_svl

                # Releer el precio de costo
                product.sudo().read(['standard_price'])

                # Obtener el margen de ganancia
                margin_gain = (
                    product.product_tmpl_id.margin_gain
                    if product.product_tmpl_id.margin_gain > 0
                    else product.product_tmpl_id.categ_id.margin_gain
                )

                # Calcular el nuevo precio sugerido basado en el precio de costo actualizado
                if margin_gain > 0:
                    new_sale_price = product.standard_price * (1 + margin_gain)                    
                    product.sudo().write({'suggested_value': new_sale_price})

                # Calcular el nuevo precio de venta sugerido
                suggested_value = 0.0
                if margin_gain > 0:
                    suggested_value = product.standard_price * (1 + margin_gain)

                # Prepare data for the wizard line
                wizard_lines_data.append({
                    'product_id': product.id,
                    'suggested_value': suggested_value,
                    'currency_id': product.currency_id.id,
                })

            move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            cost_vals = {'state': 'done'}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({'account_move_id': move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()
            cost.reconcile_landed_cost()

        # Create the wizard
        if wizard_lines_data:
            wizard = self.env['stock.landed.costs.wizard'].create({
                'line_ids': [(0, 0, line) for line in wizard_lines_data]
            })
            return {
                'name': _('Aprobar Precios de Venta'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.landed.costs.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }
        return True
