# -*- coding: utf-8 -*-
"""
Created on 2025-12-02 16:47:29

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MpPurchaseRequisitionWizard(models.TransientModel):
    _name = 'mp.purchase.requisition.wizard'
    _description = 'Multiple Product Purchase Requisition Wizard'

    department_id = fields.Many2one(
        'hr.department', string="Departamento", readonly=True)
    allowed_product_ids = fields.Many2many(
        related='department_id.department_product_ids', readonly=True)
    product_ids = fields.Many2many(
        'product.product', string="Select Products", required=True, domain="[('purchase_ok', '=', True), ('id', 'in', allowed_product_ids)]")
    
    def confirm_requisition_product(self):
        active_id = self.env.context.get('active_ids', []) or self.env.context.get('active_id')
        if not active_id:
             return 

        if isinstance(active_id, list):
            active_id = active_id[0]

        get_active_id = self.env['purchase.requisition'].browse(active_id) 
        line_env = self.env['purchase.requisition.line']
        
        if get_active_id.approval_status == 'draft':
            for wizard in self:
                for product in wizard.product_ids:
                    line_env.create({
                        'product_id': product.id,
                        'requisition_id': get_active_id.id,
                        'quantity': 1,
                        'product_uom': product.uom_id.id, 
                    })
                    
        return True
