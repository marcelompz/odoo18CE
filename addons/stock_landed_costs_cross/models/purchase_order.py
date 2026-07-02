# -*- coding: utf-8 -*-
"""
Created on 2025-03-25 16:15:23

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils

_logger = logging.getLogger(__name__)


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    adjust_sale_price = fields.Boolean(
        string='Ajustar precio de venta', default=False,
        help='Actualiza de forma automática los precios de ventas de cada producto comprado con el porcentaje de ganancia configurado previamente.')
    purchase_tooltip = fields.Char(
        compute='_compute_purchase_tooltip')
    exchange_type = fields.Monetary(
        string='Tasa de cambio', tracking=True)
    is_company_currency = fields.Boolean(
        string='Es moneda de la compañia?', compute='_compute_is_company_currency')
    is_an_import = fields.Boolean(
        string='Es una importación', default=False, tracking=True)

    @api.constrains('exchange_type')
    def _check_exchange_type(self):
        for rec in self:
            if not rec.is_company_currency and rec.exchange_type <= 0:
                raise ValidationError(_('Debes especificar una tasa de cambio válida. Valor actual: %s') % rec.exchange_type)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        self.exchange_type = self.currency_id._convert(
            1,
            self.env.company.currency_id,
            self.env.company,
            fields.Date.context_today(self),
        )
    
    @api.depends('currency_id')
    def _compute_is_company_currency(self):
        for rec in self:
            rec.is_company_currency = rec.currency_id == rec.env.company.currency_id

    @api.depends('adjust_sale_price')
    def _compute_purchase_tooltip(self):
        for rec in self:
            rec.purchase_tooltip = _('Es aconsejable habilitar esta opción sólo cuando es una compra interna, si se quiere actualizar de forma automática el precio de venta')

    def button_confirm(self):
        # Verificar si es una importación
        if self.is_an_import:
            # Eliminar los IVAs de los productos si están presentes
            for line in self.order_line:
                line.taxes_id = [(5, 0, 0)]
        
        # Si no se está trabajando en la moneda de la compañía, realizar conversiones de moneda
        if not self.is_company_currency:
            self._set_purchase_exchange()
            self._compute_currency_rate()
            self._compute_amount_total_cc()

        # Si hay ajuste de precio y es importación, reseteamos el flag
        if self.adjust_sale_price and self.is_an_import:
            self.adjust_sale_price = False

        # Actualiza el margen de ganancia del producto
        for line in self.order_line:
            if line.product_margin_gain != line.product_id.product_tmpl_id.margin_gain:
                line.product_id.product_tmpl_id.margin_gain = line.product_margin_gain

        return super().button_confirm()

    def action_create_invoice(self):
        # Llamar al método original para crear la factura
        res = super().action_create_invoice()

        # Verificar si es una importación
        for order in self:
            if order.is_an_import:
                # Buscar líneas de compra asociadas a esta orden
                purchase_lines = self.env['purchase.order.line'].search([('order_id', '=', order.id)])

                if purchase_lines:
                    # Obtener las facturas relacionadas con estas líneas de compra
                    invoices = self.env['account.move'].search([
                        ('invoice_line_ids.purchase_line_id', 'in', purchase_lines.ids)
                    ])

                    if invoices:
                        for invoice in invoices:
                            try:
                                invoice.button_create_landed_costs()
                            except Exception as e:
                                raise UserError(f"Error al intentar crear un coste en destino en factura {invoice.name}: {e}")

        return res

    def _set_purchase_exchange(self):
        """
        Ajusta la tasa de cambio para una compra si la moneda es diferente a la de la compañía.
        """
        if self.currency_id != self.env.company.currency_id:
            currency_date = self.date_approve or fields.Date.context_today(self)
            currency_rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', self.currency_id.id),
                ('name', '=', currency_date)
            ], limit=1)

            # Redondear la tasa de cambio para asegurar precisión
            exchange_rate = round(self.exchange_type or 1.0, 3)

            if currency_rate:
                currency_rate.write({'inverse_company_rate': exchange_rate})
            else:
                self.env['res.currency.rate'].create({
                    'name': currency_date,
                    'inverse_company_rate': exchange_rate,
                    'currency_id': self.currency_id.id,
                })


class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    product_margin_gain = fields.Float(
        string='%Margen', default=0.0, help='Margen de ganancia para el precio de venta')
    
    @api.onchange('product_id')
    def onchange_product_id_for_margin_gain(self):
        self.product_margin_gain = self.product_id.product_tmpl_id.margin_gain or self.product_id.product_tmpl_id.categ_id.margin_gain
