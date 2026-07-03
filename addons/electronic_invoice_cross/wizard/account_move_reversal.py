# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:42:52

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveReversalInherit(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        cdc = False
        
        if len(self.move_ids) == 1:
            cdc = self.move_ids[0].cdc_l10n_py

        stamped = self.env['account.authorization'].search([('latam_doc_type_id.code','=',5)], order='id desc', limit=1)
        format_id = self.env['res.document.format'].search([('code','=','1')])
        format_type_id = self.env['res.document.format.type'].search([('code','=','1')])
        res.update({
            'authorization_id': stamped.id if stamped else False,
            'associated_document': cdc,
            'doc_format_id': format_id.id,
            'doc_format_type_id': format_type_id.id,
        })
        
        return res
