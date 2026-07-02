# -*- coding: utf-8 -*-
"""
Created on 2026-01-23 13:18:54

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequisitionCancelWizard(models.TransientModel):
    _name = 'purchase.requisition.cancel.wizard'
    _description = 'Asistente de Cancelación de Requisición'

    requisition_id = fields.Many2one(
        'purchase.requisition', string='Requisición', required=True)
    reason = fields.Text(
        string='Motivo de Cancelación', required=True)

    def action_confirm_cancel(self):
        """
        Escribe el motivo en la requisición y cambia el estado a cancelado.
        """
        self.ensure_one()
        
        self.requisition_id.write({
            'cancellation_reason': self.reason,
            'approval_status': 'cancel'
        })

        self.requisition_id.message_post(
            body=f"Requisición cancelada. Motivo: {self.reason}",
            subtype_xmlid="mail.mt_note"
        )

        return {'type': 'ir.actions.act_window_close'}
