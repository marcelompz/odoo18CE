# -*- coding: utf-8 -*-
"""
Created on 2025-05-14 13:03:43

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    cheque_customer = fields.Many2one(
        'account.account', string='Cuenta de cheques para el cliente')
    cheque_supplier = fields.Many2one(
        'account.account', string='Cuenta de cheques para el proveedor')
    auto_fill_open_invoice = fields.Boolean(
        string = 'Autocompletar factura abierta en verificación en la selección del cliente')
    cheque_operation_type = fields.Selection(
        string='Tipo de operación', default='cancel', 
        selection=[('cancel', 'Sólo cancelar'), ('cancel_draft', 'Cancelar y reestablecer a borrador'), ('cancel_delete', 'Cancelar y eliminar')])

    # Customer
    is_cust_due_notify = fields.Boolean(
        string='Notificación de vencimiento al cliente')
    is_notify_to_customer = fields.Boolean(
        string='Notificar al cliente')
    is_notify_to_user = fields.Boolean(
        string='Notificar al usuario interno')
    cmc_user_ids = fields.Many2many(
        'res.users', string='Usuario responsable', relation='cmc_user_ids_customer_company_rel')
    notify_on_1 = fields.Char(
        string='Notificar el 1')
    notify_on_2 = fields.Char(
        string='Notificar el 2')
    notify_on_3 = fields.Char(
        string='Notificar el 3')
    notify_on_4 = fields.Char(
        string='Notificar el 4')
    notify_on_5 = fields.Char(
        string='Notificar el 5')
    
    # Supplier
    is_supplier_due_notify = fields.Boolean(
        string='Notificación de vencimiento del proveedor')
    is_notify_to_supplier = fields.Boolean(
        string='Notificar al proveedor')
    is_notify_to_user_supplier = fields.Boolean(
        string='Notificar al usuario interno')
    cmc_user_ids_supplier = fields.Many2many(
        'res.users', string='Usuario responsable', relation='cmc_user_ids_supplier_company_rel')
    notify_on_1_supplier = fields.Char(
        string='Notificar el 1')
    notify_on_2_supplier = fields.Char(
        string='Notificar el 2')
    notify_on_3_supplier = fields.Char(
        string='Notificar el 3')
    notify_on_4_supplier = fields.Char(
        string='Notificar el 4')
    notify_on_5_supplier = fields.Char(
        string='Notificar el 5')
