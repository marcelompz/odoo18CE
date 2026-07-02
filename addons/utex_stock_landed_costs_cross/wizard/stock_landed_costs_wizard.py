# -*- coding: utf-8 -*-
"""
Created on 2025-04-22 13:53:46

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockLandedCostsWizard(models.TransientModel):
    _name = 'stock.landed.costs.wizard'
    _description = 'Stock Landed Costs Wizard'

    line_ids = fields.One2many(
        'stock.landed.costs.line.wizard', 'wizard_id')

    def action_done(self):
        for line in self.line_ids:
            line.product_id.sudo().write({
                'coefficient_value': line.coefficient_value,
                'list_price': line.suggested_value,
            })
        return {'type': 'ir.actions.act_window_close'}


class StockLandedCostsLineWizard(models.TransientModel):
    _name = 'stock.landed.costs.line.wizard'
    _description = 'Stock Landed Costs Line Wizard'

    wizard_id = fields.Many2one(
        'stock.landed.costs.wizard', ondelete='cascade', index=True, string='Wizard')
    product_id = fields.Many2one(
        'product.product', string='Producto')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda')
    coefficient_value = fields.Monetary(
        string='Coeficiente', currency_field='currency_id', related='product_id.coefficient_value', store=True, readonly=False)
    suggested_value = fields.Monetary(
        string='Valor sugerido', currency_field='currency_id')
