# -*- coding: utf-8 -*-
###############################################################################
#
#  Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
###############################################################################

from odoo import models, fields,api
from datetime import datetime
import logging
_logger=logging.getLogger(__name__)

class ShopTheLook(models.Model):
    _name="shop.the.look"
    _description = "Shop the Look"

    name = fields.Char(string="Name",required=True)
    description = fields.Text(string="Description")
    banner = fields.Image(string="Banner")
    primary_image = fields.Image(string="Cover Image", required=True)
    is_published = fields.Boolean(string="Published")
    looks_ids = fields.One2many("shop.the.look.product","look_id")
    look_image_ids = fields.One2many('product.image', 'shop_the_look_id', string="Extra Product Media", copy=True)
    html_data = fields.Text(string="Description")


    @api.model
    def get_html_data(self,resId):
        data = self.env['shop.the.look'].browse(int(resId))
        if data.exists():
            return data.html_data
        return False
    
    @api.model
    def set_html_data(self,*args,**kw):
        user_data = self.env['shop.the.look'].search([("id","=",kw.get('res_id'))])
        user_data.write({
            'html_data':kw.get('data')
        })
        return True

    def _get_images(self):
        self.ensure_one()
        result =  [self] + list(self.look_image_ids)
        return result



    def website_publish_button(self):
        self.is_published = not self.is_published


    def get_details(self, *args):
        looks  = [[look.name, look.product_tmpl_id.id, look.id] for look in self.looks_ids]

        result = {
            "image" : self.primary_image,
            "looks_ids" : looks,
        }
        return result

    def empty_hotspot_position(self,*args,**kw):
        data = self.env["shop.the.look"].search([("id","=",int(kw.get("id")))])
        for look_id in data.looks_ids:
            look_data = self.env["shop.the.look.product"].browse(look_id.id)
            look_data.write({
                "hotspot_position_x" : 0, 
                "hotspot_position_y" : 0,  

            })



    def shop_look_carousel(self,*args,**kw):
        if kw.get('id'):
            look = self.browse(int(kw.get('id')))
            looks_line = self.env['shop.the.look.product'].browse(int(kw.get('line')))
            looks_line.write({
                "hotspot_position_x" : kw.get('position_x'),
                "hotspot_position_y" : kw.get('position_y'),
                "product_target" : kw.get('target'),
            })
    
    def set_hotspot_position(self,*args,**kw):
        if kw.get('id'):
            look = self.browse(int(kw.get('id')))
            looks_line = self.env['shop.the.look.product'].browse(int(kw.get('line')))
            looks_line.write({
                "hotspot_position_x" : kw.get('position_x'),
                "hotspot_position_y" : kw.get('position_y'),
                "product_target" : kw.get('target'),
            })



