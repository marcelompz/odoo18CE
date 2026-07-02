# -*- coding: utf-8 -*-
###############################################################################
#
#  Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
###############################################################################


from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers import main


import logging
_logger=logging.getLogger(__name__)


class WebsiteSale(main.WebsiteSale):

    @http.route("/shop/look/cart/update",type="json",website=True,auth='public',csrf=False)
    def cart_update_look(self, set_qty=None, *args, **kwargs):
        product_ids = kwargs.get('product_id')
        add_qty = kwargs.get('add_qty')
        for product in product_ids :
            val = self.cart_update_json(product_id=product, add_qty=add_qty,*args)
        return True


class Menu_Controller(http.Controller):


    @http.route(["/lookbook/","/lookbook/<int:id>"],method=['GET'],type="http", auth="public",website=True)
    def shop_the_look_data(self, id=None, **post):
        if id:
            shop_the_look_data = request.env['shop.the.look'].sudo().search([("id", "=", id),('is_published','=',True)], limit=1)
            values = {'records':shop_the_look_data}
            return request.render('shop_the_look.shop_the_look_temp',values)
        else:
            current_website = request.env['website'].get_current_website()
            values = {
                'records':current_website
            }
            return request.render('shop_the_look.look_book_temp',values)
