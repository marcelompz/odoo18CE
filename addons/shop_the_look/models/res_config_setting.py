# -*- coding: utf-8 -*-
###############################################################################
#
#  Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
###############################################################################


from odoo import fields, models, _

from logging import getLogger
_logger = getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    banner = fields.Image(string="Banner Image", related='website_id.banner', readonly=False)
    banner_text = fields.Text(string="Banner Text", related='website_id.banner_text', readonly=False)
    description = fields.Text(string="Description", related='website_id.look_description', readonly=False)
    button_title = fields.Text(string="Button Title", related='website_id.button_title', readonly=False)
    display_type = fields.Selection(related='website_id.display_type', string='Type of View', readonly=False, required=True)
    look_ids = fields.Many2many('shop.the.look', string="Look Collection", related="website_id.look_ids", domain="[('is_published', '=', True)]", readonly=False)
