# -*- coding: utf-8 -*-
###############################################################################
#
#  Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
###############################################################################

from odoo import api, fields, models, tools, _

from logging import getLogger
_logger = getLogger(__name__)


class ProductImage(models.Model):
    _inherit = 'product.image'
    
    shop_the_look_id = fields.Many2one('shop.the.look', "Shop The Look", index=True, ondelete='cascade')
    
    
    
