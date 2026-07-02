# -*- coding: utf-8 -*-
"""
Created on 2025-05-14 13:03:57

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    cheque_customer = fields.Many2one(
        'account.account', related='company_id.cheque_customer', readonly=False)
    cheque_supplier = fields.Many2one(
        'account.account', related='company_id.cheque_supplier', readonly=False)
    auto_fill_open_invoice = fields.Boolean(
        related='company_id.auto_fill_open_invoice', readonly=False)
    cheque_operation_type = fields.Selection(
        related='company_id.cheque_operation_type', readonly=False)

    # Customer
    is_cust_due_notify = fields.Boolean(
        related='company_id.is_cust_due_notify', readonly=False)
    is_notify_to_customer = fields.Boolean(
        related='company_id.is_notify_to_customer', readonly=False)
    is_notify_to_user = fields.Boolean(
        related='company_id.is_notify_to_user', readonly=False)
    cmc_user_ids = fields.Many2many(
        'res.users', related='company_id.cmc_user_ids', readonly=False)
    notify_on_1 = fields.Char(
        related='company_id.notify_on_1', readonly=False)
    notify_on_2 = fields.Char(
        related='company_id.notify_on_2', readonly=False)
    notify_on_3 = fields.Char(
        related='company_id.notify_on_3', readonly=False)
    notify_on_4 = fields.Char(
        related='company_id.notify_on_4', readonly=False)
    notify_on_5 = fields.Char(
        related='company_id.notify_on_5', readonly=False)
    
    # Supplier
    is_supplier_due_notify = fields.Boolean(
        related='company_id.is_supplier_due_notify', readonly=False)
    is_notify_to_supplier = fields.Boolean(
        related='company_id.is_notify_to_supplier', readonly=False)
    is_notify_to_user_supplier = fields.Boolean(
        related='company_id.is_notify_to_user_supplier', readonly=False)
    cmc_user_ids_supplier = fields.Many2many(
        'res.users', related='company_id.cmc_user_ids_supplier', readonly=False)
    notify_on_1_supplier = fields.Char(
        related='company_id.notify_on_1_supplier', readonly=False)
    notify_on_2_supplier = fields.Char(
        related='company_id.notify_on_2_supplier', readonly=False)
    notify_on_3_supplier = fields.Char(
        related='company_id.notify_on_3_supplier', readonly=False)
    notify_on_4_supplier = fields.Char(
        related='company_id.notify_on_4_supplier', readonly=False)
    notify_on_5_supplier = fields.Char(
        related='company_id.notify_on_5_supplier', readonly=False)
