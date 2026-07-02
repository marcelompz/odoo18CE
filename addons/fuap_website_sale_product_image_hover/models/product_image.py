# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ProductImage(models.Model):
    _inherit = 'product.image'
    
    hover = fields.Boolean(_("Image hover"), help=_("Enable this option to define that this image will be displayed when hovering over the product image"), default=False)

    @api.model_create_multi
    def create(self, vals_list):
        
        for image in vals_list:
            self.clear_image_hover(image.get('product_tmpl_id'))

        return super(ProductImage, self).create(vals_list)
        
    def write(self, data):

        if data.keys() & {'hover'} and data.get('hover', False) == True:
            self.clear_image_hover(self.product_tmpl_id.id)
        
        return super(ProductImage, self).write(data)
        
    def clear_image_hover(self, product_tmpl_id):
        ctx = dict(self.env.context)

        if not ctx.get('product_image_hover', False):
            images = self.search([('product_tmpl_id', '=', product_tmpl_id)])

            if images:
                images.with_context(product_image_hover=True).write({'hover': False})