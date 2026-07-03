# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:31:56

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    def action_view_delivery(self):
        """
        Actualiza el contexto de la vista de albaranes para filtrar los de tipo 'outgoing'.
        """
        res = super().action_view_delivery()
        res['context'].update({'picking_type_code': 'outgoing'})
        return res

    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            payment_term = order.partner_id.property_payment_term_id

            if not payment_term:
                # Buscar el término de pago inmediato
                payment_term = self.env['account.payment.term'].search(
                    [('is_cash_payment', '=', True)], 
                    limit=1, 
                    order='id desc'
                )
            
            order.payment_term_id = payment_term

    def _prepare_invoice(self):
        res = super()._prepare_invoice()

        stamped = self.env['account.authorization'].search([('latam_doc_type_id.code','=',1)], order='id desc', limit=1)
        
        res.update({
            'authorization_id': stamped.id if stamped else False,
        })
        
        return res


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line()

        if self.company_id.without_discount_invoice:
            res.update({
                'price_unit': self.price_reduce_taxinc,
                'discount': 0.0,
            })
        return res
