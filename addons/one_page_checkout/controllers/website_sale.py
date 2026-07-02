# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Autor: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    Puedes modificarlo bajo los términos de la GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Versión 3.
#
#    Este programa se distribuye con la esperanza de que sea útil,
#    pero SIN NINGUNA GARANTÍA; sin incluso la garantía implícita de
#    COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.  Consulta la
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) para más detalles.
#
#    Deberías haber recibido una copia de la GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) junto con este programa.
#    Si no, consulta <https://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json
from odoo import models, fields
import base64


class WebsiteSaleEcom(WebsiteSale):
    """
    Versión personalizada del controlador de ventas para e-commerce.
    """

    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'],
                auth="public", website=True, sitemap=False)
    def address(self, **kw):
        order = request.website.sale_get_order()
        if order:
            user = request.website.user_id.sudo()
            if order.partner_id.id == user.partner_id.id:
                return request.redirect('/shop/payment')
            else:
                partner = order.partner_id.sudo()
                countries = request.env['res.country'].search([])
                country = partner.country_id
                # Puedes adaptar estos valores según tu lógica
                checkout = {}  # Aquí puedes poner los datos del formulario si los tienes
                error = {}     # Aquí puedes poner errores de validación si los tienes
                mode = 'edit'  # O el modo que corresponda
                only_services = order.only_services if hasattr(order, 'only_services') else False
                is_public_user = request.website.is_public_user()
                return request.render('website_sale.address', {
                    'website_sale_order': order,
                    'partner_sudo': order.partner_id.sudo(),
                    'countries': request.env['res.country'].search([]),
                    'country': order.partner_id.country_id,
                    'checkout': {},  # O los datos del formulario si los tienes
                    'error': {},
                    'mode': 'edit',
                    'only_services': getattr(order, 'only_services', False),
                    'is_public_user': request.website.is_public_user(),
                })
        return request.redirect('/shop/payment')

    @http.route(['/shop/extra_info'], type='http', auth="public", website=True,
                sitemap=False)
    def extra_info(self):
        return request.redirect('/shop/payment')

    @http.route('/shop/payment', type='http', auth='public', website=True,
                sitemap=False)
    def shop_payment(self, **post):
        post.update({'partner_id': -1})
        order = request.website.sale_get_order()
        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False
        render_values['deliveries'] = order._get_delivery_methods().sudo()
        render_values['delivery_action_id'] = request.env.ref(
            'delivery.action_delivery_carrier_form'
        ).id
        render_values['sale_order_id'] = order.id

        if render_values['errors']:
            render_values.pop('providers', '')
            render_values.pop('tokens', '')
        request.session['sale_last_order_id'] = order.id
        return request.render("website_sale.payment", render_values)

    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def custom_checkout_redirect(self, **kw):
        return request.redirect('/shop/payment')

    @http.route('/one_page_checkout/get_address', type='http', auth='public', website=True, methods=['GET'])
    def get_address(self, **kw):
        address_id = kw.get('address_id')
        if not address_id:
            return request.make_response('{}', [('Content-Type', 'application/json')])
        partner = request.env['res.partner'].sudo().browse(int(address_id))
        if not partner.exists():
            return request.make_response('{}', [('Content-Type', 'application/json')])
        data = {
            'name': partner.name or '',
            'street': partner.street or '',
            'city': partner.city or '',
            'zip': partner.zip or '',
            'phone': partner.phone or '',
            'email': partner.email or '',
            'vat': partner.vat or '',
            'country_id': partner.country_id.id if partner.country_id else '',
            'state_id': partner.state_id.id if partner.state_id else '',
        }
        return request.make_response(json.dumps(data), [('Content-Type', 'application/json')])

    @http.route('/one_page_checkout/save_address', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def save_address(self, **post):
        import json
        address_id = post.get('address_id')
        values = {
            'name': post.get('name'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'phone': post.get('phone'),
        }
        address_type = post.get('address_type', 'billing')
        try:
            if address_id:
                partner = request.env['res.partner'].sudo().browse(int(address_id))
                if partner.exists():
                    partner.write(values)
                    # Asignar la dirección editada al pedido según el tipo
                    order = request.website.sale_get_order()
                    if order:
                        if address_type == 'billing':
                            order.partner_id = partner.id
                        else:
                            order.partner_shipping_id = partner.id
                else:
                    return request.make_response(json.dumps({'success': False, 'error': 'Dirección no encontrada.'}), [('Content-Type', 'application/json')])
            else:
                order = request.website.sale_get_order()
                if not order:
                    return request.make_response(json.dumps({'success': False, 'error': 'No hay pedido activo.'}), [('Content-Type', 'application/json')])
                new_partner = request.env['res.partner'].sudo().create(values)
                if address_type == 'billing':
                    order.partner_id = new_partner.id
                else:
                    order.partner_shipping_id = new_partner.id
            return request.make_response(json.dumps({'success': True}), [('Content-Type', 'application/json')])
        except Exception as e:
            return request.make_response(json.dumps({'success': False, 'error': str(e)}), [('Content-Type', 'application/json')])

    @http.route('/one_page_checkout/country_states', type='json', auth='public', website=True)
    def country_states(self):
        countries = request.env['res.country'].sudo().search([])
        result = []
        for country in countries:
            states = [{'id': s.id, 'name': s.name} for s in country.state_ids]
            result.append({
                'id': country.id,
                'name': country.name,
                'states': states,
            })
        return result





class WebsiteSaleCustom(http.Controller):

    @http.route('/website/form/shop.sale.order', type='http', auth="public", website=True, csrf=False)
    def website_form_saleorder(self, **kwargs):
        # Llama al método original para crear la orden
        response = super().website_form_saleorder(**kwargs)
        order = request.website.sale_get_order()
        # Guardar el adjunto como comentario
        attachment_ids = []
        if order and 'a_document' in request.httprequest.files:
            file_storage = request.httprequest.files['a_document']
            file_content = file_storage.read()
            attachment = request.env['ir.attachment'].sudo().create({
                'name': file_storage.filename,
                'datas': base64.b64encode(file_content).decode('utf-8'),
                'res_model': 'sale.order',
                'res_id': order.id,
                'type': 'binary',
                'mimetype': file_storage.mimetype,
            })
            attachment_ids.append(attachment.id)
        # Guardar referencia y opinión como comentario
        ref = kwargs.get('client_order_ref')
        opinion = kwargs.get('Danos tu opinión')
        comment_lines = []
        if ref:
            comment_lines.append(f"<b>Referencia del cliente:</b> {ref}")
        if opinion:
            comment_lines.append(f"<b>Opinión del cliente:</b> {opinion}")
        if attachment_ids:
            comment_lines.append("Comprobante de pago adjuntado desde el checkout.")
        if comment_lines:
            order.message_post(
                body="<br/>".join(comment_lines),
                attachment_ids=attachment_ids
            )
        return response
