# -*- coding: utf-8 -*-
"""
Created on 2025-03-13 17:55:31

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    is_send_de = fields.Boolean(
        string='Es un correo para enviar documentos electrónicos', default=False)

    @api.constrains('is_send_de')
    def _check_is_send_de(self):
        for record in self:
            if record.is_send_de:
                existing = self.search([('is_send_de', '=', True), ('id', '!=', record.id)])
                if existing:
                    raise ValidationError(_('Solo un registro puede tener el campo "Es un correo para enviar documentos electrónicos" marcado.'))
