# -*- coding: utf-8 -*-
"""
Created on 2025-07-30 15:21:19

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'
    
    def add_withholdings(self):
        view_id = self.env.ref('advanced_receiptmoney_cross.add_withholdings_receiptmoney_wizard_form')

         # Obtener el valor de 'resId' del contexto actual
        contexto_actual = self.env.context
        res_id = contexto_actual.get('params', {}).get('resId')

        if not res_id:
            raise UserError(_("No se pudo encontrar el ID del registro en el contexto."))

        if view_id:
            details_wiz_data = {
                'name': _('Agregar retención'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'add.withholdings.receiptmoney.wizard',
                'target': 'new',
                'view_id': view_id.id,
                'context': {
                    'receiptmoney_id': res_id,
                    'move_id': self.id,
                    'currency_id': self.currency_id.id,
                },
            }
		
        return details_wiz_data
