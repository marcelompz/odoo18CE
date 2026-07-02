# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _pos_ui_models_to_load(self):
        """Sobrescribe el método para incluir image_1920 en los datos del POS"""
        models_to_load = super()._pos_ui_models_to_load()
        
        # Buscar el modelo 'product.product' en la lista
        for model in models_to_load:
            if model.get('model') == 'product.product':
                # Añadir image_1920 a los campos a cargar
                fields_to_load = model.get('fields', [])
                if 'image_1920' not in fields_to_load:
                    fields_to_load.append('image_1920')
                # También añadir image_1024 como fallback
                if 'image_1024' not in fields_to_load:
                    fields_to_load.append('image_1024')
                model['fields'] = fields_to_load
                break
        
        return models_to_load

    def _get_pos_ui_product_product(self, params):
        """Sobrescribe el método para asegurar que image_1920 se incluya en los productos"""
        products = super()._get_pos_ui_product_product(params)
        
        # Asegurar que cada producto tenga image_1920 e image_1024
        for product in products:
            if 'image_1920' not in product:
                product['image_1920'] = False
            if 'image_1024' not in product:
                product['image_1024'] = False
        
        return products
