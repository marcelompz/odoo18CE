# -*- coding: utf-8 -*-

import json
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError
import io
import xlsxwriter


class PortalDetailController(http.Controller):

    @http.route(['/portal/upload-details'], type='http', auth="public", website=True)
    def portal_upload_details(self, **kw):
        """Formulario para cargar detalles desde el portal"""
        order_id = kw.get('order_id')
        token = kw.get('token')

        # Validar token de edición
        if not order_id or not token:
            return request.redirect('/my?error=missing_params')

        try:
            # Usar token de edición para acceder al pedido
            order = request.env['sale.order'].sudo().browse(int(order_id))
            if not order.exists():
                return request.redirect('/my?error=order_not_found')

            # Verificar token de edición
            if not order._portal_ensure_token():
                return request.redirect('/my?error=invalid_token')

            if order.access_token != token:
                return request.redirect('/my?error=invalid_token')

            # Buscar configuración activa para este pedido
            config = request.env['portal.detail.config'].sudo().search([
                ('order_id', '=', order.id),
                ('is_active', '=', True),
                ('state', '=', 'active')
            ], limit=1)

            if not config:
                return request.redirect('/my?error=no_config_found')

            # Verificar fecha de expiración
            if config.expires_date and config.expires_date < fields.Datetime.now():
                config.action_expire()
                return request.redirect('/my?error=config_expired')

            # Renderizar formulario
            return request.render('portal_detalles.portal_upload_form_template', {
                'config': config,
                'order': order,
                'customer': order.partner_id,
                'categories': config.available_categories,
                'sizes': config.available_sizes,
            })

        except (ValueError, TypeError):
            return request.redirect('/my?error=invalid_params')
        except Exception as e:
            return request.redirect(f'/my?error=server_error&message={str(e)}')

    @http.route(['/portal/upload-details/submit'], type='http', auth="public", website=True, methods=['POST'], csrf=True)
    def portal_upload_details_submit(self, **post):
        """Procesar el envío de la lista"""
        try:
            # Obtener parámetros
            order_id = post.get('order_id')
            token = post.get('token')
            rows_data = post.get('rows_data', '[]')
            customer_notes = post.get('customer_notes', '')

            # Validar parámetros
            if not order_id or not token:
                return request.redirect('/my?error=missing_params')

            # Validar token de edición
            order = request.env['sale.order'].sudo().browse(int(order_id))
            if not order.exists():
                return request.redirect('/my?error=order_not_found')

            if order.access_token != token:
                return request.redirect('/my?error=invalid_token')

            # Buscar configuración activa
            config = request.env['portal.detail.config'].sudo().search([
                ('order_id', '=', order.id),
                ('is_active', '=', True),
                ('state', '=', 'active')
            ], limit=1)

            if not config:
                return request.redirect('/my?error=no_config_found')

            # Procesar datos JSON
            try:
                items_data = json.loads(rows_data)
            except (json.JSONDecodeError, TypeError) as e:
                return request.redirect('/my?error=invalid_data')

            # Validar que haya datos
            if not items_data:
                return request.redirect('/my?error=no_data')

            # Crear lista
            detail_list = request.env['portal.detail.list'].sudo().create({
                'name': f"LIST-{config.order_id.name}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
                'config_id': config.id,
                'customer_notes': customer_notes,
                'state': 'submitted',
                'submitted_date': fields.Datetime.now(),
            })

            # Crear items
            for item_data in items_data:
                # Validar campos requeridos
                if not item_data.get('modelo') or not item_data.get('producto1') or not item_data.get('talle1'):
                    continue

                request.env['portal.detail.item'].sudo().create({
                    'list_id': detail_list.id,
                    'modelo': item_data.get('modelo', ''),
                    'nombre': item_data.get('nombre', ''),
                    'numero': item_data.get('numero', ''),
                    'otros': item_data.get('otros', ''),
                    'cantidad': int(item_data.get('cantidad', 1)),
                    'producto1': item_data.get('producto1', ''),
                    'talle1': item_data.get('talle1', ''),
                    'producto2': item_data.get('producto2', ''),
                    'talle2': item_data.get('talle2', ''),
                    'producto3': item_data.get('producto3', ''),
                    'talle3': item_data.get('talle3', ''),
                    'producto4': item_data.get('producto4', ''),
                    'talle4': item_data.get('talle4', ''),
                    'producto5': item_data.get('producto5', ''),
                    'talle5': item_data.get('talle5', ''),
                })

            # Enviar notificación
            detail_list._send_notification_to_commercial()

            # Redirigir a página de éxito
            return request.render('portal_detalles.portal_success_template', {
                'detail_list': detail_list,
                'config': config,
                'order': detail_list.order_id,
                'customer': detail_list.customer_id,
            })

        except Exception as e:
            # Log del error para debugging
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error processing portal details: {str(e)}")
            return request.redirect(f'/my?error=processing_error&message={str(e)}')

    def _validate_portal_token(self, order_id, token):
        """Validar token de portal del pedido"""
        if not order_id or not token:
            return False

        try:
            order = request.env['sale.order'].sudo().browse(int(order_id))
            if not order.exists():
                return False
            
            # Verificar que el token coincida
            if order.access_token != token:
                return False
            
            return order
        except (ValueError, TypeError):
            return False

    @http.route(['/portal/upload-details/preview'], type='http', auth="public", website=True)
    def portal_upload_details_preview(self, **kw):
        """Vista previa del formulario (para testing)"""
        # Solo para desarrollo/testing
        if not request.env.user.has_group('base.group_system'):
            return request.redirect('/my')

        # Buscar una configuración activa para preview
        config = request.env['portal.detail.config'].sudo().search([
            ('is_active', '=', True),
            ('state', '=', 'active')
        ], limit=1)

        if not config:
            return request.render('portal_detalles.portal_no_config_template')

        return request.render('portal_detalles.portal_upload_form_template', {
            'config': config,
            'order': config.order_id,
            'customer': config.customer_id,
            'categories': config.available_categories,
            'sizes': config.available_sizes,
        })

    @http.route(['/portal/upload-details/status/<int:list_id>'], type='http', auth="public", website=True)
    def portal_upload_details_status(self, list_id, **kw):
        """Ver estado de una lista enviada"""
        try:
            detail_list = request.env['portal.detail.list'].sudo().browse(list_id)
            if not detail_list.exists():
                return request.redirect('/my?error=list_not_found')

            # Verificar que el usuario tenga acceso (mismo cliente)
            if request.env.user.partner_id != detail_list.customer_id:
                return request.redirect('/my?error=access_denied')

            return request.render('portal_detalles.portal_status_template', {
                'detail_list': detail_list,
                'config': detail_list.config_id,
                'order': detail_list.order_id,
                'customer': detail_list.customer_id,
            })

        except Exception as e:
            return request.redirect('/my?error=processing_error')

    @http.route(['/portal_detalles/export_xlsx/<int:list_id>'], type='http', auth="user")
    def export_list_xlsx(self, list_id, **kw):
        """Exportar los items de una lista a XLSX"""
        detail_list = request.env['portal.detail.list'].sudo().browse(list_id)
        if not detail_list.exists():
            return request.not_found()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Items')

        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#EEEEEE'})
        headers = ['Modelo', 'Nombre', 'Número', 'Otros', 'Cantidad',
                   'Producto 1', 'Talle 1', 'Producto 2', 'Talle 2',
                   'Producto 3', 'Talle 3', 'Producto 4', 'Talle 4',
                   'Producto 5', 'Talle 5']
        for col, h in enumerate(headers):
            worksheet.write(0, col, h, header_fmt)

        row = 1
        for item in detail_list.detail_items:
            values = [
                item.modelo or '', item.nombre or '', item.numero or '', item.otros or '', item.cantidad or 1,
                item.producto1 or '', item.talle1 or '', item.producto2 or '', item.talle2 or '',
                item.producto3 or '', item.talle3 or '', item.producto4 or '', item.talle4 or '',
                item.producto5 or '', item.talle5 or '',
            ]
            for col, v in enumerate(values):
                worksheet.write(row, col, v)
            row += 1

        workbook.close()
        output.seek(0)

        filename = f"Lista_{detail_list.name}.xlsx"
        headers_out = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ]
        return request.make_response(output.read(), headers=headers_out)

    @http.route(['/portal/upload-details/api/categories'], type='json', auth="public", website=True)
    def api_get_categories(self, config_id=None):
        """API para obtener categorías disponibles"""
        try:
            if config_id:
                config = request.env['portal.detail.config'].sudo().browse(config_id)
                if config.exists() and config.is_active:
                    categories = config.available_categories
                else:
                    return {'error': 'Config not found or inactive'}
            else:
                categories = request.env['product.category'].sudo().search([])

            return {
                'categories': [
                    {
                        'id': cat.id,
                        'name': cat.name,
                    } for cat in categories
                ]
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route(['/portal/upload-details/api/sizes'], type='json', auth="public", website=True)
    def api_get_sizes(self, config_id=None):
        """API para obtener talles disponibles"""
        try:
            if config_id:
                config = request.env['portal.detail.config'].sudo().browse(config_id)
                if config.exists() and config.is_active:
                    sizes = config.available_sizes
                else:
                    return {'error': 'Config not found or inactive'}
            else:
                # Buscar valores del atributo "Talle"
                talle_attribute = request.env['product.attribute'].sudo().search([
                    ('name', 'ilike', 'talle')
                ], limit=1)
                
                if talle_attribute:
                    sizes = talle_attribute.value_ids
                else:
                    # Fallback: buscar cualquier atributo que contenga "talle" en el nombre
                    sizes = request.env['product.attribute.value'].sudo().search([
                        ('attribute_id.name', 'ilike', 'talle')
                    ])

            return {
                'sizes': [
                    {
                        'id': size.id,
                        'name': size.name,
                    } for size in sizes
                ]
            }
        except Exception as e:
            return {'error': str(e)}
