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
from odoo.addons.website.controllers.form import WebsiteForm
import logging
_logger = logging.getLogger(__name__)


class WebsiteSaleForm(WebsiteForm):
    """
    Class representing a form for ecommerce checkout.
    Inherits:
    WebsiteForm: The base class for website forms, providing common
    functionalities.
    Usage:
    1. Create an instance of `WebsiteSaleForm` and customize it as needed.
    2. Use the instance to handle the checking out in your shop.
    """

    @http.route('/website/form/shop.sale.order', type='http', auth="public",
                methods=['POST'], website=True)
    def website_form_saleorder(self, **kwargs):
        """
        This function is called when the user submits the checkout form for a
        sales order on the website. It first calls the parent method `website_
        form_sale_order` to handle the submission of the form and create the
        sales order. Then, it retrieves the created sales order from the
        website session and stores its ID in the user's session. Finally,
        it redirects the user to the payment status page.

        :param kwargs: Optional keyword arguments.
        :return: A redirect to the payment status page.
        """
        super(WebsiteSaleForm, self).website_form_saleorder(**kwargs)
        order = request.website.sale_get_order()
       # if request.session.get('sale_last_order_id') is None and order:
        #    request.session['sale_last_order_id'] = order.id
       # return request.redirect('/payment/status')
        render_values = self._get_shop_payment_values(order, **kwargs)
        render_values['deliveries'] = order._get_delivery_methods().sudo()
        return request.render("website_sale.payment", render_values)

    @http.route('/one_page_checkout/get_address', type='http', auth='public', website=True, methods=['GET'])
    def get_address(self, **kw):
        import json
        address_id = kw.get('address_id')
        _logger.warning(f"address_id recibido: {address_id}, kw: {kw}")
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
        address_id = post.get('address_id')
        values = {
            'name': post.get('name'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'phone': post.get('phone'),
        }
        try:
            if address_id:
                partner = request.env['res.partner'].sudo().browse(int(address_id))
                if partner.exists():
                    partner.write(values)
                else:
                    return request.make_response(json.dumps({'success': False, 'error': 'Dirección no encontrada.'}), [('Content-Type', 'application/json')])
            else:
                order = request.website.sale_get_order()
                if not order:
                    return request.make_response(json.dumps({'success': False, 'error': 'No hay pedido activo.'}), [('Content-Type', 'application/json')])
                new_partner = request.env['res.partner'].sudo().create(values)
                order.partner_shipping_id = new_partner.id
            return request.make_response(json.dumps({'success': True}), [('Content-Type', 'application/json')])
        except Exception as e:
            return request.make_response(json.dumps({'success': False, 'error': str(e)}), [('Content-Type', 'application/json')])
