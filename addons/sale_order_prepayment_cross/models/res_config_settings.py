# -*- coding: utf-8 -*-
"""
Created on 2025-08-15 17:27:52

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    prepayment_auto_reconcile = fields.Boolean(
        related='company_id.prepayment_auto_reconcile', readonly=False)
    advance_approval_percentag = fields.Float(
        related='company_id.advance_approval_percentag', readonly=False)
