# -*- coding: utf-8 -*-
"""
Created on 2025-05-14 13:02:56

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'
    
    sequence = fields.Integer(
        string='Secuencia')
    is_boolean = fields.Boolean(
        compute='compute_is_boolean')
    cheque_id = fields.Many2one(
        'account.cheque.payment')
    cheque_payment_ids = fields.Many2many(
        'account.cheque.payment', compute='_compute_cheque_payment_invoice', store=True)
    cheque_payment_count = fields.Integer(
        string='Recuento de pagos de cheques', compute='_compute_cheque_payment')
    total_cheque_payment = fields.Monetary(
        string='Total', compute='_compute_total_cheque')
    total_cheque_pending = fields.Monetary(
        string='Total Pendientes', compute='_compute_total_cheque')
    total_cheque_cancel = fields.Monetary(
        string='Total Cancelados', compute='_compute_total_cheque')
    total_cheque_received = fields.Monetary(
        string='Total recibido', compute='_compute_total_cheque')

    def compute_is_boolean(self):
        for rec in self:
            rec.is_boolean = False
            if rec.cheque_payment_ids.filtered(lambda x:x.state in ['registered','deposited']):
                rec.is_boolean = True

    def open_cheque_payment(self):
        [action] = self.env.ref('cheque_management_cross.account_cheque_payment_action').read()
        action['domain'] = [('id', 'in', self.cheque_payment_ids.ids)]
        return action
    
    def _compute_cheque_payment(self):
        for rec in self:
            rec.cheque_payment_count = len(self.cheque_payment_ids)

    @api.depends('cheque_payment_ids.state')
    def _compute_total_cheque(self):
        for rec in self:
            rec.total_cheque_payment = rec.total_cheque_pending = rec.total_cheque_cancel = rec.total_cheque_received = 0.0

            if rec.cheque_payment_ids:
                for cheque_payment in rec.cheque_payment_ids:
                    if cheque_payment.state in ('done'):
                        rec.total_cheque_received += cheque_payment.payment_amount
                    
                    elif cheque_payment.state in ('cancel'):
                        rec.total_cheque_cancel += cheque_payment.payment_amount
                    
                    else:
                        rec.total_cheque_pending += cheque_payment.payment_amount
            
            rec.total_cheque_payment = rec.total_cheque_pending + rec.total_cheque_received + rec.total_cheque_cancel
    
    def _compute_cheque_payment_invoice(self):
        self.cheque_payment_ids = False
        
        for move in self:
            cheques = self.env["account.cheque.payment"].search([
                '|',('invoice_id','=',move.id),('invoice_ids.id','=',move.id)
                ])
            
            if cheques:
                move.cheque_payment_ids = [(6,0,cheques.ids)]


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    cheque_id = fields.Many2one(
        'account.cheque.payment')
