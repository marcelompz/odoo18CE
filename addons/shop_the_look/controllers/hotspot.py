# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
#################################################################################
from odoo import fields, http, tools, _
from odoo.http import request, Controller
import logging
from odoo.addons.website.controllers.main import Website
_logger = logging.getLogger(__name__)

class AddHotSpot(Website):

    @http.route(['/get/product/info'], type='json', auth="public", website=True, csrf=False)
    def get_product_data(self, pid, **kwargs):      
        try:
            product_id = request.env['product.template'].sudo().browse(int(pid))
            if not product_id.exists():
                return {'error': 'Product not found'}
          
            result = {
                'product_id': product_id.id,
                'product_variant_id': product_id._get_first_possible_variant_id(),
                'name': product_id.name,
                'image': product_id.image_256
            }
            return result
        except (ValueError, TypeError):
            return {'error': 'Invalid product ID'}
