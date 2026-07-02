# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class WebsiteSaleVariantController(http.Controller):

    @http.route('/fuap/test', type='http', auth='public', website=True)
    def test_controller(self):
        """Test route to verify controller is working"""
        return "FUAP Controller is working!"

    @http.route('/fuap/check_variant_combination', type='json', auth='public', website=True)
    def check_variant_combination(self, product_id, selected_attributes):
        """Check if a combination of attributes is available"""
        try:
            # Validate input parameters
            if not product_id:
                return {'success': False, 'error': 'Product ID is required'}
            
            if not selected_attributes or not isinstance(selected_attributes, list):
                return {'success': False, 'error': 'Selected attributes must be a list'}
            
            # Get product
            product = request.env['product.product'].browse(int(product_id))
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            
            # Convert selected_attributes to the format expected by the model
            attributes_dict = {}
            for attr in selected_attributes:
                if isinstance(attr, dict) and 'attribute' in attr and 'value' in attr:
                    attributes_dict[attr['attribute']] = attr['value']
            
            is_available, variant_id = product._check_combination_availability(attributes_dict)
            
            return {
                'success': True,
                'available': is_available,
                'variant_id': variant_id,
                'message': 'Available' if is_available else 'Not available'
            }
            
        except ValueError as e:
            return {'success': False, 'error': 'Invalid product ID format'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/fuap/get_unavailable_combinations', type='json', auth='public', website=True)
    def get_unavailable_combinations(self, product_id):
        """Get all unavailable combinations for a product"""
        try:
            # Validate input parameters
            if not product_id:
                return {'success': False, 'error': 'Product ID is required'}
            
            # Get product
            product = request.env['product.product'].browse(int(product_id))
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            
            unavailable_combinations = product._get_unavailable_combinations()
            
            # Format the data for frontend use
            formatted_combinations = []
            for combination in unavailable_combinations:
                formatted_combination = {
                    'variant_id': combination['variant_id'],
                    'attributes': combination['attributes']
                }
                formatted_combinations.append(formatted_combination)
            
            return {
                'success': True,
                'unavailable_combinations': formatted_combinations
            }
            
        except ValueError as e:
            return {'success': False, 'error': 'Invalid product ID format'}
        except Exception as e:
            return {'success': False, 'error': str(e)} 