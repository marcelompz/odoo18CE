import json
from odoo import http
from odoo.http import request


class ProductVariantController(http.Controller):

    @http.route('/shop/product/get_variant_info', type='json', auth="public", website=True, csrf=False)
    def get_variant_info(self, variant_id, **kw):
        """Obtiene información de la variante de producto para actualización dinámica"""
        try:
            product_variant = request.env['product.product'].sudo().browse(int(variant_id))
            if not product_variant.exists():
                return {'error': 'Variante de producto no encontrada'}

            # Obtener imágenes de la variante
            variant_images = []
            for img in product_variant.variant_image_ids:
                variant_images.append({
                    'id': img.id,
                    'url': img.image_url,
                    'name': img.name,
                    'sequence': img.sequence
                })

            # Formatear precio
            currency = product_variant.currency_id
            formatted_price = f"{currency.symbol} {product_variant.list_price:.2f}"

            return {
                'success': True,
                'variant_id': product_variant.id,
                'name': product_variant.display_name,
                'price': product_variant.list_price,
                'formatted_price': formatted_price,
                'currency_symbol': currency.symbol,
                'main_image_url': f'/web/image/product.product/{product_variant.id}/image_1920',
                'variant_images': variant_images,
                'availability': product_variant.qty_available > 0 if hasattr(product_variant, 'qty_available') else True
            }
        except Exception as e:
            return {'error': f'Error al obtener información de la variante: {str(e)}'}

    @http.route('/shop/product/get_variant_images', type='json', auth="public", website=True, csrf=False)
    def get_variant_images(self, product_tmpl_id, **kw):
        """Obtiene todas las imágenes de variantes para un producto"""
        try:
            product_template = request.env['product.template'].sudo().browse(int(product_tmpl_id))
            if not product_template.exists():
                return {'error': 'Producto no encontrado'}

            variants_data = []
            for variant in product_template.product_variant_ids:
                variant_images = []
                for img in variant.variant_image_ids:
                    variant_images.append({
                        'id': img.id,
                        'url': img.image_url,
                        'name': img.name,
                        'sequence': img.sequence
                    })

                variants_data.append({
                    'variant_id': variant.id,
                    'variant_name': variant.display_name,
                    'price': variant.list_price,
                    'formatted_price': f"{variant.currency_id.symbol} {variant.list_price:.2f}",
                    'main_image_url': f'/web/image/product.product/{variant.id}/image_1920',
                    'variant_images': variant_images
                })

            return {
                'success': True,
                'variants': variants_data
            }
        except Exception as e:
            return {'error': f'Error al obtener imágenes de variantes: {str(e)}'}

    @http.route('/shop/product/update_variant_selection', type='json', auth="public", website=True, csrf=False)
    def update_variant_selection(self, variant_id, **kw):
        """Actualiza la selección de variante y devuelve información actualizada"""
        try:
            variant_info = self.get_variant_info(variant_id)
            if variant_info.get('error'):
                return variant_info

            # Aquí se podría agregar lógica adicional como actualizar la sesión
            # o realizar otras operaciones necesarias

            return variant_info
        except Exception as e:
            return {'error': f'Error al actualizar selección de variante: {str(e)}'}

