# -*- coding: utf-8 -*-
from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_image_hover(self):
        self.ensure_one()
        return self.product_template_image_ids.filtered(lambda x: x.hover is True)

    def _get_available_attributes(self):
        """Get available product attributes that are visible in eCommerce"""
        self.ensure_one()
        attributes = []
        for attribute_line in self.attribute_line_ids:
            # Solo incluir atributos que crean variantes
            if attribute_line.attribute_id.create_variant == 'always':
                values = []
                for value in attribute_line.value_ids:
                    values.append({
                        'id': value.id,
                        'name': value.name,
                        'html_color': value.html_color,
                    })
                attributes.append({
                    'id': attribute_line.attribute_id.id,
                    'name': attribute_line.attribute_id.name,
                    'display_type': attribute_line.attribute_id.display_type,
                    'values': values,
                })
        return attributes

    def _get_total_attributes_count(self):
        """Get total number of attributes that create variants"""
        self.ensure_one()
        return len(self.attribute_line_ids.filtered(lambda x: x.attribute_id.create_variant == 'always'))

    def _get_variant_combinations(self):
        """Get all possible variant combinations and their availability"""
        self.ensure_one()
        combinations = []
        
        # Get all product variants
        variants = self.product_variant_ids.filtered(lambda v: v.active)
        
        # Get all attribute lines
        attribute_lines = self.attribute_line_ids.filtered(lambda x: x.attribute_id.create_variant == 'always')
        
        # Create all possible combinations
        for variant in variants:
            combination = {
                'variant_id': variant.id,
                'available': variant.active and variant.sale_ok,
                'attributes': {}
            }
            
            for attribute_line in attribute_lines:
                attribute_value = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_line_id == attribute_line
                )
                if attribute_value:
                    combination['attributes'][attribute_line.attribute_id.name] = {
                        'value_id': attribute_value.product_attribute_value_id.id,
                        'value_name': attribute_value.product_attribute_value_id.name,
                        'html_color': attribute_value.product_attribute_value_id.html_color,
                    }
            
            combinations.append(combination)
        
        return combinations

    def _check_combination_availability(self, selected_attributes):
        """Check if a combination of attributes is available"""
        self.ensure_one()
        
        # Get all available combinations
        combinations = self._get_variant_combinations()
        
        # Find matching combination
        for combination in combinations:
            if combination['available']:
                match = True
                for attr_name, attr_value in selected_attributes.items():
                    if attr_name not in combination['attributes']:
                        match = False
                        break
                    if combination['attributes'][attr_name]['value_name'] != attr_value:
                        match = False
                        break
                
                if match:
                    return True, combination['variant_id']
        
        return False, None

    def _get_unavailable_combinations(self):
        """Get combinations that are not available"""
        self.ensure_one()
        unavailable = []
        
        # Get all attribute lines
        attribute_lines = self.attribute_line_ids.filtered(lambda x: x.attribute_id.create_variant == 'always')
        
        # Get all possible combinations
        combinations = self._get_variant_combinations()
        
        # Check which combinations are not available
        for combination in combinations:
            if not combination['available']:
                unavailable.append(combination)
        
        return unavailable

class Product(models.Model):
    _inherit = "product.product"

    def _get_image_hover(self):
        self.ensure_one()
        return self.product_tmpl_id._get_image_hover()

    def _get_available_attributes(self):
        """Get available product attributes from template"""
        self.ensure_one()
        return self.product_tmpl_id._get_available_attributes()

    def _get_total_attributes_count(self):
        """Get total number of attributes from template"""
        self.ensure_one()
        return self.product_tmpl_id._get_total_attributes_count()

    def _get_variant_combinations(self):
        """Get variant combinations from template"""
        self.ensure_one()
        return self.product_tmpl_id._get_variant_combinations()

    def _check_combination_availability(self, selected_attributes):
        """Check combination availability from template"""
        self.ensure_one()
        return self.product_tmpl_id._check_combination_availability(selected_attributes)

    def _get_unavailable_combinations(self):
        """Get unavailable combinations from template"""
        self.ensure_one()
        return self.product_tmpl_id._get_unavailable_combinations()