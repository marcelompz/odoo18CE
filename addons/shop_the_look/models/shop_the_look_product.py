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

class ShopTheLookProduct(models.Model):
    _name="shop.the.look.product"
    _description = "Shop the Look"
    

    name = fields.Char(string="Name")
    look_id = fields.Many2one("shop.the.look", string="Look ID")
    hotspot_position_x = fields.Float(string="Position x")
    hotspot_position_y = fields.Float(string="Position y")
    product_target = fields.Selection(selection=[('_self', 'Self'), ('_blank', 'Blank')], default="_self")
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    prod_variant_ids = fields.Many2many("product.product", domain="[('product_tmpl_id','=', product_tmpl_id )]", string="Product Variants")

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        for record in self:
            record.name = record.product_tmpl_id.name

            
    def get_look_price(self,target_currency=False):
        src_currency = self.product_tmpl_id.currency_id
        target_currency  = target_currency
        company = self.env.user.company_id
        date = datetime.now()
        list_price = self.product_tmpl_id.list_price

        converted_price = src_currency._convert(list_price,target_currency,company,date)
        return round(converted_price,2)
    
    
    
    

