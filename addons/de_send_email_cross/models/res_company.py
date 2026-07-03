# -*- coding: utf-8 -*-
"""
Created on 2025-04-30 12:34:57

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    send_de_copy_to = fields.Boolean(
        string='Enviar copia?', default=False)
    email_to_copy_de = fields.Char(
        string='Enviar copia a')
    

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    send_de_copy_to = fields.Boolean(
        related='company_id.send_de_copy_to', readonly=False)
    email_to_copy_de = fields.Char(
        related='company_id.email_to_copy_de', readonly=False)

    
