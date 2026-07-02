from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import base64
import json


class WebsiteSaleSimplified(WebsiteSale):

    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def redirect_checkout(self, **post):
        return request.redirect('/shop/checkout/simplified')

    @http.route(['/shop/checkout/simplified'], type='http', auth="public", website=True, sitemap=False)
    def checkout_simplified(self, **post):
        """
        Ruta para el checkout simplificado que combina dirección y pago
        """
        order = request.website.sale_get_order()
        if not order or not order.order_line or order.state != 'draft':
            return request.redirect('/shop')

        # Obtener datos necesarios para el checkout
        countries = request.env['res.country'].sudo().search([])
        # Buscar Paraguay como país predeterminado
        paraguay = request.env['res.country'].sudo().search([('code', '=', 'PY')], limit=1)
        default_country_id = paraguay.id if paraguay else countries[0].id if countries else False
        
        states = request.env['res.country.state'].sudo().search([])
        payment_methods = request.env['payment.provider'].sudo().search([
            ('state', 'in', ['enabled', 'test'])
        ])

        values = {
            'order': order,
            'countries': countries,
            'states': states,
            'payment_methods': payment_methods,
            'partner': order.partner_id,
            'default_country_id': default_country_id,
            'errors': {},
            'error_message': [],
            'country': order.partner_id.country_id if order.partner_id else None,
            'form_data': {},
        }

        # Procesar formulario si es POST
        if request.httprequest.method == 'POST':
            return self._process_simplified_checkout(post, values)

        return request.render('web_checkout_simplifier.checkout', values)

    def _process_simplified_checkout(self, post, values):
        """
        Procesa el formulario de checkout simplificado
        """
        order = values['order']
        errors = {}

        # Validar datos de dirección
        required_fields = ['name', 'email', 'street', 'city', 'country_id']
        for field in required_fields:
            if not post.get(field):
                errors[field] = 'Este campo es requerido'

        # Validar método de pago
        if not post.get('payment_method'):
            errors['payment_method'] = 'Debe seleccionar un método de pago'

        if errors:
            values['errors'] = errors
            values['form_data'] = post
            return request.render('website_sale.checkout', values)

        # Actualizar o crear partner
        partner_values = {
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
            'street': post.get('street'),
            'street2': post.get('street2'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'country_id': int(post.get('country_id')),
            'state_id': int(post.get('state_id')) if post.get('state_id') else False,
        }

        if order.partner_id and order.partner_id != request.website.user_id.partner_id:
            order.partner_id.write(partner_values)
        else:
            partner = request.env['res.partner'].sudo().create(partner_values)
            order.partner_id = partner.id

        # Procesar archivo adjunto ANTES de confirmar la orden (como en el ejemplo)
        if 'checkout_file' in request.httprequest.files:
            file_upload = request.httprequest.files['checkout_file']
            if file_upload.filename:
                file_data = base64.b64encode(file_upload.read())
                
                # Crear attachment como en el ejemplo
                payment_proof_attachment = request.env['ir.attachment'].sudo().create({
                    'name': file_upload.filename,
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'type': 'binary',
                    'public': True,
                    'datas': file_data,
                })
                
                # Agregar mensaje como comentario (similar al ejemplo)
                body = _("Comprobante de pago %s subido por %s durante el checkout") % (
                    file_upload.filename, 
                    request.env.user.name if request.env.user.name != 'Public user' else 'Cliente'
                )
                order.message_post(body=body, attachment_ids=[payment_proof_attachment.id])
                
                # Guardar referencia en campos específicos
                order.write({
                    'checkout_attachment': file_data,
                    'checkout_attachment_name': file_upload.filename
                })

        # Procesar pago
        payment_method_id = int(post.get('payment_method'))
        payment_method = request.env['payment.provider'].sudo().browse(payment_method_id)

        # Si es transferencia bancaria, agregar nota especial
        if payment_method.code == 'transfer':
            bank_note = post.get('bank_transfer_note', '')
            if bank_note:
                note_body = _("Nota de transferencia bancaria: %s") % bank_note
                order.message_post(body=note_body)
                
                if order.note:
                    order.note = f"{order.note}\n\n{note_body}"
                else:
                    order.note = note_body

        # Confirmar la orden DESPUÉS de procesar el comprobante
        order.action_confirm()

        # Redirigir a la página de Mis Pedidos mostrando el pedido creado
        return request.redirect(f'/my/orders/{order.id}')

    @http.route(['/shop/checkout/get_states'], type='json', auth="public", website=True)
    def get_states(self, country_id):
        """
        Obtiene los estados de un país específico vía AJAX
        """
        states = request.env['res.country.state'].sudo().search([
            ('country_id', '=', int(country_id))
        ])
        return [{
            'id': state.id,
            'name': state.name,
            'code': state.code
        } for state in states]

    @http.route(['/shop/checkout/get_payment_info'], type='json', auth="public", website=True)
    def get_payment_info(self, payment_method_id):
        """
        Obtiene información específica del método de pago
        """
        payment_method = request.env['payment.provider'].sudo().browse(int(payment_method_id))
        return {
            'code': payment_method.code,
            'name': payment_method.name,
            'instructions': payment_method.pre_msg or '',
            'is_transfer': payment_method.code == 'transfer'
        }

    @http.route(['/shop/update_address'], type='json', auth="public", website=True, csrf=False)
    def dummy_update_address(self, **kwargs):
        # Puedes imprimir kwargs para ver qué parámetros llegan
        return {'result': 'ok'}

