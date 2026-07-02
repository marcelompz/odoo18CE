# -*- coding: utf-8 -*-
###############################################################################
#
#  Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
###############################################################################


from odoo import api, fields, models, tools, _

class Website(models.Model):
    _inherit = "website"

    banner = fields.Image(string="Image")
    look_description = fields.Text(string="Description")
    button_title = fields.Text(string="Button Title")
    banner_text = fields.Text(string="Banner Text")
    display_type = fields.Selection(selection=[('fixed', 'Fixed'), ('carousel', 'Carousel'),('list','List')], default="list")
    look_ids = fields.Many2many("shop.the.look")

    def res_config_values(self):
        banner = self.env['ir.config_parameter'].sudo().get_param('shop_the_look.banner')
        description = self.env['ir.config_parameter'].sudo().get_param('shop_the_look.description')
        display_type = self.env['ir.config_parameter'].sudo().get_param('shop_the_look.display_type')
        banner_text = self.env['ir.config_parameter'].sudo().get_param('shop_the_look.banner_text')
        button_title = self.env['ir.config_parameter'].sudo().get_param('shop_the_look.button_title')
        return {
            'banner':banner,
            'description' : description,
            'display_type' : display_type, 
            'banner_text' : banner_text,
            'button_title' : button_title
        }
