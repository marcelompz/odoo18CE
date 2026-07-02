# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Aysha Shalin (odoo@cybrosys.com)
#
#    you can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC
#    LICENSE (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.addons.payment.controllers import portal as payment_portal

from odoo.http import route, request
from odoo.tools import str2bool
from odoo.addons.website_sale.controllers.main import WebsiteSale
import base64
from odoo import http
import logging
_logger = logging.getLogger(__name__)


class WebsiteSaleCustom(WebsiteSale):
    # tu código aquí

    #@route(['/shop/checkout'], type='http', auth='public', website=True, sitemap=False, enctype='multipart/form-data')
    #def shop_checkout(self, try_skip_step=None, **query_params):
       # """
       # Redirige automáticamente a /shop/payment si el usuario ya tiene dirección.
       # """
       # order = request.website.sale_get_order()
        # Si el pedido ya tiene dirección de envío y facturación, redirige a payment
      #  if order and order.partner_shipping_id and order.partner_invoice_id:
      #      return request.redirect('/shop/payment')
        # Si no, muestra el checkout estándar
     #   return super().shop_checkout(try_skip_step=try_skip_step, **query_params)

    def _clean_session_for_new_order(self, current_order):
        """
        Limpia la sesión para asegurar que esté sincronizada con la orden actual
        """
        if not current_order:
            return
            
        # Limpiar archivos temporales de órdenes anteriores
        temp_receipt = request.session.get('temp_transfer_receipt')
        if temp_receipt:
            stored_order_id = temp_receipt.get('order_id')
            if stored_order_id and stored_order_id != current_order.id:
                request.session.pop('temp_transfer_receipt', None)
        
        # Limpiar información de transferencia de órdenes anteriores
        if 'bank_transfer_checkout' in request.session:
            request.session.pop('bank_transfer_checkout', None)
            
        # Asegurar que sale_last_order_id esté actualizado
        if request.session.get('sale_last_order_id') != current_order.id:
            request.session['sale_last_order_id'] = current_order.id

    @route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, try_skip_step=None, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.provider. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling
        """
        try_skip_step = str2bool(try_skip_step or 'false')
        order_sudo = request.website.sale_get_order()

        # Limpiar y sincronizar la sesión con la orden actual
        if order_sudo:
            self._clean_session_for_new_order(order_sudo)

        checkout_page_values = self._prepare_checkout_page_values(order_sudo, **post)

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        render_values = self._get_shop_payment_values(order_sudo, **post)
        render_values['only_services'] = order_sudo and order_sudo.only_services

        can_skip_delivery = True  # Delivery is only needed for deliverable products.
        if order_sudo._has_deliverable_products():
            available_dms = order_sudo._get_delivery_methods()
            checkout_page_values['delivery_methods'] = available_dms
            if delivery_method := order_sudo._get_preferred_delivery_method(
                    available_dms):
                rate = delivery_method.rate_shipment(order_sudo)
                render_values['delivery_methods'] = checkout_page_values['delivery_methods']
                if (
                        not order_sudo.carrier_id
                        or not rate.get('success')
                        or order_sudo.amount_delivery != rate['price']
                ):
                    order_sudo._set_delivery_method(delivery_method, rate=rate)
            can_skip_delivery = self.can_skip_delivery_step(order_sudo,
                                                            available_dms)

        if try_skip_step and can_skip_delivery:
                return request.redirect('/shop/confirm_order')

        if render_values['errors']:
            render_values.pop('payment_methods_sudo', '')
            render_values.pop('tokens_sudo', '')
        
        # Agregar variable para mostrar la sección de comprobante de transferencia
        render_values['show_transfer_receipt'] = True
        
        # Agregar contenido HTML directamente para debug
        render_values['transfer_receipt_html'] = '''
        <div class="card mt-3">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fa fa-receipt me-2"></i>
                    Comprobante de Transferencia (Opcional)
                </h5>
            </div>
            <div class="card-body">
                <div class="alert alert-info">
                    <i class="fa fa-info-circle me-2"></i>
                    <strong>Importante:</strong> Si selecciona transferencia bancaria, puede subir el comprobante de pago aquí. 
                    El archivo se guardará como comentario en su pedido antes de la confirmación.
                </div>
                <div class="mb-3">
                    <label for="transfer_receipt_file" class="form-label">
                        Subir comprobante de transferencia
                    </label>
                    <input type="file" 
                           class="form-control" 
                           id="transfer_receipt_file" 
                           name="bank_transfer_receipt" 
                           accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.txt"/>
                    <div class="form-text">
                        Formatos permitidos: PDF, JPG, PNG, DOC, DOCX, TXT. Tamaño máximo: 10MB
                    </div>
                    <div id="transfer_file_info" class="mt-2" style="display: none;">
                        <div class="alert alert-success py-2">
                            <i class="fa fa-check-circle me-2"></i>
                            <span id="transfer_file_name"></span>
                            <small class="d-block text-muted" id="transfer_file_size"></small>
                        </div>
                    </div>
                </div>
                
                <script type="text/javascript">
                    document.addEventListener('DOMContentLoaded', function() {
                        var fileInput = document.getElementById('transfer_receipt_file');
                        
                        if (fileInput) {
                            // Asegurar que el formulario tenga enctype
                            var form = fileInput.closest('form');
                            if (form) {
                                form.setAttribute('enctype', 'multipart/form-data');
                            }
                            
                            // Agregar evento de cambio para enviar archivo
                            fileInput.addEventListener('change', function() {
                                var file = this.files[0];
                                if (file) {
                                    // Validar tipo de archivo
                                    var allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt'];
                                    var fileName = file.name.toLowerCase();
                                    var isValidType = allowedTypes.some(function(type) {
                                        return fileName.endsWith(type);
                                    });
                                    
                                    if (!isValidType) {
                                        alert('Tipo de archivo no permitido. Use: PDF, JPG, PNG, DOC, DOCX, TXT');
                                        this.value = '';
                                        return;
                                    }
                                    
                                    // Validar tamaño (10MB)
                                    if (file.size > 10 * 1024 * 1024) {
                                        alert('El archivo es demasiado grande. Máximo 10MB.');
                                        this.value = '';
                                        return;
                                    }
                                    
                                    // Mostrar información del archivo
                                    var fileInfo = document.getElementById('transfer_file_info');
                                    var fileNameSpan = document.getElementById('transfer_file_name');
                                    var fileSizeSpan = document.getElementById('transfer_file_size');
                                    
                                    fileNameSpan.textContent = file.name;
                                    fileSizeSpan.textContent = 'Tamaño: ' + (file.size / 1024 / 1024).toFixed(2) + ' MB';
                                    fileInfo.style.display = 'block';
                                    
                                    // Cambiar el estilo para mostrar que se está enviando
                                    fileInfo.className = 'alert alert-info py-2';
                                    fileNameSpan.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Enviando archivo...';
                                    
                                    // Enviar archivo al servidor
                                    var formData = new FormData();
                                    formData.append('bank_transfer_receipt', file);
                                    
                                    fetch('/shop/store_transfer_receipt', {
                                        method: 'POST',
                                        body: formData
                                    })
                                    .then(function(response) {
                                        return response.json();
                                    })
                                    .then(function(data) {
                                        if (data.success) {
                                            // Mostrar éxito
                                            fileInfo.className = 'alert alert-success py-2';
                                            fileNameSpan.innerHTML = '<i class="fa fa-check-circle me-2"></i>' + file.name;
                                            fileSizeSpan.innerHTML = '<small class="d-block text-muted">Archivo guardado correctamente</small>';
                                        } else {
                                            // Mostrar error
                                            fileInfo.className = 'alert alert-danger py-2';
                                            fileNameSpan.innerHTML = '<i class="fa fa-exclamation-circle me-2"></i>Error al guardar archivo';
                                            fileSizeSpan.innerHTML = '<small class="d-block text-muted">' + data.message + '</small>';
                                            fileInput.value = '';
                                        }
                                    })
                                    .catch(function(error) {
                                        // Mostrar error de red
                                        fileInfo.className = 'alert alert-danger py-2';
                                        fileNameSpan.innerHTML = '<i class="fa fa-exclamation-circle me-2"></i>Error de conexión';
                                        fileSizeSpan.innerHTML = '<small class="d-block text-muted">No se pudo enviar el archivo</small>';
                                        fileInput.value = '';
                                    });
                                }
                            });
                        }
                    });
                </script>
            </div>
        </div>
        '''
        
        return request.render("website_sale.payment", render_values)

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment_confirmation(self, **post):
        """ Página de confirmación del pedido """
        # Obtener la orden de la sesión
        sale_order_id = request.session.get('sale_last_order_id')
        bank_transfer_checkout = request.session.pop('bank_transfer_checkout', False)
        
        if sale_order_id:
            # Buscar la orden y verificar que existe
            order = request.env['sale.order'].sudo().browse(sale_order_id).exists()
            if order:
                # Usar el método estándar de Odoo para preparar los valores
                values = super()._prepare_shop_payment_confirmation_values(order)
                values['bank_transfer_checkout'] = bank_transfer_checkout
                return request.render("website_sale.confirmation", values)
            else:
                pass
        
        # Si no hay orden válida, redirigir a la tienda
        return request.redirect('/shop')

    @http.route('/shop/store_transfer_receipt', type='http', auth="public", website=True, methods=['POST'], csrf=False, enctype='multipart/form-data')
    def store_transfer_receipt(self, **post):
        """ Almacena temporalmente el archivo de comprobante en la sesión """
        file = request.httprequest.files.get('bank_transfer_receipt')
        if file and file.filename:
            try:
                file_data = base64.b64encode(file.read())
                
                # Obtener la orden actual
                order = request.website.sale_get_order()
                order_id = order.id if order else None
                
                # Almacenar en sesión temporalmente con el ID de la orden
                request.session['temp_transfer_receipt'] = {
                    'data': file_data.decode('utf-8'),
                    'filename': file.filename,
                    'order_id': order_id
                }
                
                return http.Response(
                    '{"success": true, "message": "Archivo almacenado correctamente"}',
                    content_type='application/json'
                )
                
            except Exception as e:
                return http.Response(
                    '{"success": false, "message": "Error al almacenar archivo"}',
                    content_type='application/json'
                )
        else:
            return http.Response(
                '{"success": false, "message": "No se encontró archivo"}',
                content_type='application/json'
            )

    # Comentamos el método confirm_order personalizado ya que no se usa en el flujo estándar
    # @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, csrf=False, enctype='multipart/form-data')
    # def confirm_order(self, **post):
    #     # Este método se comentó porque no se usa en el flujo estándar de Odoo
    #     pass

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **post):
        """ Procesa el adjunto antes de validar la orden en el flujo estándar de Odoo. """
        
        if sale_order_id is None:
            order = request.website.sale_get_order()
            
            # Si no hay orden activa, intentar obtener la última orden de la sesión
            if not order and 'sale_last_order_id' in request.session:
                last_order_id = request.session['sale_last_order_id']
                order = request.env['sale.order'].sudo().browse(last_order_id).exists()
                
                # Verificar si esta orden es realmente la más reciente
                if order:
                    # Buscar la orden más reciente del usuario actual
                    user_orders = request.env['sale.order'].sudo().search([
                        ('partner_id', '=', order.partner_id.id),
                        ('state', 'in', ['draft', 'sent', 'sale'])
                    ], order='create_date desc', limit=1)
                    
                    if user_orders and user_orders.id != order.id:
                        order = user_orders
                        # Actualizar la sesión con la orden correcta
                        request.session['sale_last_order_id'] = order.id
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if order:
            pass
        else:
            pass

        # Detectar si es transferencia bancaria basándose en la transacción
        is_bank_transfer = False
        tx_sudo = order.get_portal_last_transaction() if order else order.env['payment.transaction']
        if tx_sudo and tx_sudo.provider_id:
            # Verificar si el proveedor de pago es de transferencia bancaria
            provider_name = tx_sudo.provider_id.name.lower()
            if any(keyword in provider_name for keyword in ['transfer', 'bank', 'bancaria', 'transferencia']):
                is_bank_transfer = True
                _logger.info(f"Detectado método de pago de transferencia: {tx_sudo.provider_id.name}")

        # Procesar comprobante de transferencia si existe en la sesión y corresponde a esta orden
        temp_receipt = request.session.get('temp_transfer_receipt')
        if temp_receipt and order:
            # Verificar que el archivo corresponda a esta orden
            stored_order_id = temp_receipt.get('order_id')
            if stored_order_id == order.id:
                try:
                    file_data = temp_receipt['data'].encode('utf-8')
                    
                    # Procesar el adjunto usando el método del modelo
                    result = order._process_transfer_receipt_attachment(file_data, temp_receipt['filename'])
                    
                    # Marcar en sesión si es transferencia
                    request.session['bank_transfer_checkout'] = True
                    
                    # Limpiar archivo temporal de la sesión
                    request.session.pop('temp_transfer_receipt', None)
                        
                except Exception as e:
                    pass
            else:
                # Limpiar archivo temporal de la sesión si no corresponde
                request.session.pop('temp_transfer_receipt', None)
        elif is_bank_transfer:
            # Si es transferencia bancaria pero no hay comprobante, también marcar
            request.session['bank_transfer_checkout'] = True

        # --- Copia el resto de la lógica estándar de Odoo ---
        errors = self._get_shop_payment_errors(order)
        if errors:
            first_error = errors[0]  # only display first error
            error_msg = f"{first_error[0]}\n{first_error[1]}"
            from odoo.exceptions import ValidationError
            raise ValidationError(error_msg)

        tx_sudo = order.get_portal_last_transaction() if order else order.env['payment.transaction']

        if not order or (order.amount_total and not tx_sudo):
            return request.redirect('/shop')

        if order and not order.amount_total and not tx_sudo:
            if order.state != 'sale':
                order._validate_order()
            request.website.sale_reset()
            return request.redirect(order.get_portal_url())

        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == 'draft':
            return request.redirect('/shop')

        return request.redirect('/shop/confirmation')

    @http.route('/shop/address/submit', type='http', methods=['POST'], auth='public', website=True, sitemap=False)
    def shop_address_submit(self, partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None, required_fields=None, **form_data):
        """ Maneja el envío del formulario de dirección, incluyendo registro para usuarios anónimos """
        
        # Verificar si es un formulario de registro unificado
        if 'register_name' in form_data and 'register_email' in form_data and 'register_password' in form_data:
            # Es un formulario de registro unificado
            return self._handle_unified_registration_address(form_data, address_type, use_delivery_as_billing, callback)
        else:
            # Es el formulario estándar de dirección
            return super().shop_address_submit(partner_id, address_type, use_delivery_as_billing, callback, required_fields, **form_data)
    


    def _handle_unified_registration_address(self, form_data, address_type, use_delivery_as_billing, callback):
        """ Maneja el registro unificado de usuario y dirección """
        
        try:
            # Extraer datos del formulario unificado
            register_name = form_data.get('register_name')
            register_email = form_data.get('register_email')
            register_password = form_data.get('register_password')
            register_phone = form_data.get('register_phone')
            register_street = form_data.get('register_street')
            register_street2 = form_data.get('register_street2', '')
            register_city = form_data.get('register_city')
            register_zip = form_data.get('register_zip')
            register_country_id = form_data.get('register_country_id')
            # Campo de estado oculto - no se procesa
            register_state_id = False
            
            # Validar campos requeridos
            required_fields = [register_name, register_email, register_password, register_phone, 
                             register_street, register_city, register_zip, register_country_id]
            
            if not all(required_fields):
                return request.redirect('/shop/address')
            
            # OPCIÓN 3: Crear usuario activo y usar flujo nativo de Odoo
            
            # Obtener el ID del grupo portal de forma segura
            try:
                portal_group = request.env['res.groups'].sudo().search([('name', '=', 'Portal')], limit=1)
                if portal_group:
                    portal_group_id = portal_group.id
                else:
                    portal_group_id = 9
            except Exception as e:
                portal_group_id = 9
            
            # Crear usuario ACTIVO (pero usar flujo nativo para activación)
            user_vals = {
                'name': register_name,
                'login': register_email,
                'password': register_password,
                'email': register_email,
                'groups_id': [(6, 0, [portal_group_id])],  # Usuario portal
                'active': True,  # Usuario ACTIVO desde el principio
                'signature': '',  # Sin firma por defecto
            }
            
            # Crear el usuario activo
            user = request.env['res.users'].sudo().create(user_vals)
            
            # Crear el partner de tipo cliente
            partner_vals = {
                'name': register_name,
                'email': register_email,
                'phone': register_phone,
                'street': register_street,
                'street2': register_street2,
                'city': register_city,
                'zip': register_zip,
                'country_id': int(register_country_id),
                'user_id': user.id,
                'is_company': False,  # Es una persona, no una empresa
                'customer_rank': 1,   # Cliente con ranking
                'supplier_rank': 0,   # No es proveedor
            }
            
            # Campo de estado oculto - no se asigna
            # if register_state_id:
            #     partner_vals['state_id'] = int(register_state_id)
            
            partner = request.env['res.partner'].sudo().create(partner_vals)
            
            # Actualizar el usuario con el partner
            user.sudo().write({'partner_id': partner.id})
            
            # OPCIÓN 3: Usar flujo nativo de Odoo para activación y autenticación
            
            try:
                # Verificar que el usuario está activo (ya lo está desde la creación)
                if user.active:
                    pass
                else:
                    user.sudo().write({'active': True})
                
            except Exception as activation_error:
                pass
            
            # Verificar que el usuario se creó correctamente como Portal
            user_groups = [g.id for g in user.groups_id]
            if portal_group_id not in user_groups:
                user.sudo().write({'groups_id': [(4, portal_group_id)]})
            else:
                pass
            
            # Actualizar la orden de venta
            order = request.website.sale_get_order()
            if order:
                if address_type == 'billing':
                    order.sudo().write({'partner_invoice_id': partner.id})
                elif address_type == 'shipping':
                    order.sudo().write({'partner_shipping_id': partner.id})
                
                # Si use_delivery_as_billing está marcado, usar la misma dirección
                if use_delivery_as_billing == 'on':
                    order.sudo().write({
                        'partner_invoice_id': partner.id,
                        'partner_shipping_id': partner.id
                    })
            else:
                pass
            
            # Commit para asegurar que todo esté guardado
            request.env.cr.commit()
            
            # OPCIÓN 3: Autenticar usando el flujo nativo de Odoo
            return self._native_authentication(user, register_email, register_password, order)
                
        except Exception as e:
            return request.redirect('/shop/address')

    def _simple_portal_authentication(self, user, email, password, order):
        """ Método simple de autenticación para usuarios portal """
        try:
            _logger.info("🔄 Intentando autenticación simple para portal...")
            
            # Establecer la sesión directamente con el usuario creado
            _logger.info(f"Estableciendo sesión directamente para usuario: {user.name} (ID: {user.id})")
            
            # Establecer la sesión manualmente
            request.session.uid = user.id
            request.session.login = user.login
            request.session.db = request.db
            
            # Generar token de sesión usando el método estándar de Odoo
            try:
                request.session.session_token = user.sudo()._compute_session_token(request.session.sid)
                _logger.info("✅ Token de sesión estándar generado")
            except Exception as token_error:
                _logger.warning(f"No se pudo generar token de sesión estándar: {str(token_error)}")
                # Fallback: token simple
                try:
                    import hashlib
                    import time
                    token_data = f"{user.id}:{request.session.sid}:{time.time()}"
                    request.session.session_token = hashlib.sha256(token_data.encode()).hexdigest()
                    _logger.info("✅ Token de sesión fallback generado")
                except Exception as fallback_error:
                    _logger.error(f"Error generando token fallback: {str(fallback_error)}")
            
            # Verificar que la sesión se estableció correctamente
            if request.session.uid == user.id:
                _logger.info(f"✅ Sesión establecida correctamente para usuario: {user.name}")
                _logger.info(f"Session UID: {request.session.uid}")
                _logger.info(f"Session Login: {request.session.login}")
                _logger.info(f"Session Token: {'***' if request.session.session_token else 'NO'}")
                
                # Actualizar la orden con el usuario
                if order:
                    order.sudo().write({'user_id': user.id})
                    _logger.info(f"Orden actualizada con usuario: {order.name}")
                
                # Commit de la transacción para asegurar persistencia
                request.env.cr.commit()
                _logger.info("✅ Transacción confirmada")
                
                # Intentar autenticación estándar para asegurar persistencia
                try:
                    _logger.info("Intentando autenticación estándar para confirmar sesión...")
                    uid = request.session.authenticate(request.db, user.login, password)
                    if uid and uid == user.id:
                        _logger.info(f"✅ Autenticación estándar exitosa: {uid}")
                    else:
                        _logger.warning(f"Autenticación estándar falló: {uid}")
                except Exception as auth_error:
                    _logger.warning(f"Error en autenticación estándar: {str(auth_error)}")
                
                _logger.info("✅ Redirigiendo a /shop/payment después de autenticación simple")
                return request.redirect('/shop/payment')
            else:
                _logger.error("❌ No se pudo establecer la sesión")
                return self._alternative_authentication(user, email, password, order)
                
        except Exception as e:
            _logger.error(f"Error en autenticación simple: {str(e)}")
            return self._alternative_authentication(user, email, password, order)

    def _alternative_authentication(self, user, email, password, order):
        """ Método alternativo de autenticación """
        try:
            _logger.info("🔄 Intentando autenticación estándar de Odoo...")
            
            # Commit de la transacción para asegurar que el usuario esté disponible
            request.env.cr.commit()
            _logger.info("✅ Transacción confirmada antes de autenticación")
            
            # Limpiar la sesión actual
            request.session.logout(keep_db=True)
            _logger.info("✅ Sesión limpiada")
            
            # Intentar autenticación estándar
            _logger.info(f"Intentando autenticar: {email}")
            uid = request.session.authenticate(request.db, email, password)
            _logger.info(f"Resultado de autenticación: {uid}")
            
            if uid and uid != request.env.ref('base.public_user').id:
                _logger.info(f"✅ Autenticación estándar exitosa: {email} (UID: {uid})")
                
                # Verificar que la sesión está activa
                if request.session.uid == uid:
                    _logger.info("✅ Sesión confirmada")
                    
                    # Actualizar la orden con el usuario autenticado
                    if order:
                        order.sudo().write({'user_id': uid})
                        _logger.info(f"Orden actualizada con usuario: {order.name}")
                    
                    # Commit final
                    request.env.cr.commit()
                    _logger.info("✅ Transacción final confirmada")
                    
                    _logger.info("✅ Redirigiendo a /shop/payment después de autenticación estándar")
                    return request.redirect('/shop/payment')
                else:
                    _logger.warning("❌ Sesión no confirmada después de autenticación")
                    return self._final_authentication_attempt(user, email, password, order)
            else:
                _logger.error("❌ Autenticación estándar falló")
                return self._final_authentication_attempt(user, email, password, order)
                
        except Exception as e:
            _logger.error(f"Error en autenticación estándar: {str(e)}")
            return self._final_authentication_attempt(user, email, password, order)

    def _final_authentication_attempt(self, user, email, password, order):
        """ Método final de autenticación como último recurso """
        try:
            _logger.info("🔄 Método final: Usuario creado exitosamente")
            
            _logger.info(f"✅ Usuario {user.name} creado exitosamente")
            _logger.info(f"✅ Email: {email}")
            _logger.info(f"✅ Contraseña: ***")
            _logger.info(f"✅ Redirigiendo a login para autenticación manual")
            
            # Redirigir a la página de login con mensaje de éxito
            return request.redirect('/web/login?redirect=/shop/payment&registration=success')
                
        except Exception as e:
            _logger.error(f"Error en método final: {str(e)}")
            return request.redirect('/web/login?redirect=/shop/payment&error=final_error')

    def _native_authentication(self, user, email, password, order):
        """ Método de autenticación directa estableciendo la sesión manualmente """
        try:
            _logger.info("🔄 OPCIÓN 3: Iniciando autenticación directa...")
            _logger.info(f"Usuario: {user.name}, Email: {email}")
            
            # PRESERVAR EL CARRITO ANTES DE LA AUTENTICACIÓN
            _logger.info("🔄 Preservando carrito antes de autenticación...")
            
            # Guardar información del carrito actual
            cart_order_id = None
            if order:
                cart_order_id = order.id
                _logger.info(f"Carrito actual: {order.name} (ID: {cart_order_id})")
            
            # Verificar que el usuario está activo
            if not user.active:
                _logger.info("Activando usuario...")
                user.sudo().write({'active': True})
                request.env.cr.commit()
            
            # Commit para asegurar que el usuario esté disponible
            request.env.cr.commit()
            _logger.info("Transacción confirmada")
            
            # Establecer la sesión directamente
            _logger.info("Estableciendo sesión manualmente...")
            
            # Limpiar la sesión actual PERO preservar el carrito
            request.session.logout(keep_db=True)
            
            # Establecer la sesión directamente con el usuario creado
            request.session.uid = user.id
            request.session.login = user.login
            request.session.db = request.db
            
            # RESTAURAR EL CARRITO DESPUÉS DE LA AUTENTICACIÓN
            if cart_order_id:
                _logger.info(f"🔄 Restaurando carrito: {cart_order_id}")
                request.session['sale_last_order_id'] = cart_order_id
                _logger.info(f"Carrito restaurado en sesión: {cart_order_id}")
            
            # Generar token de sesión simple
            try:
                import hashlib
                import time
                token_data = f"{user.id}:{request.session.sid}:{time.time()}"
                request.session.session_token = hashlib.sha256(token_data.encode()).hexdigest()
                _logger.info("Token de sesión generado")
            except Exception as token_error:
                _logger.warning(f"Error generando token: {str(token_error)}")
            
            # Verificar que la sesión se estableció correctamente
            _logger.info(f"Session UID: {request.session.uid}")
            _logger.info(f"User ID: {user.id}")
            
            if request.session.uid == user.id:
                _logger.info("Sesión establecida correctamente")
                
                # RESTAURAR Y ACTUALIZAR LA ORDEN CON EL USUARIO AUTENTICADO
                if cart_order_id:
                    _logger.info(f"🔄 Restaurando orden: {cart_order_id}")
                    
                    # Buscar la orden en el nuevo contexto de usuario
                    restored_order = request.env['sale.order'].sudo().browse(cart_order_id).exists()
                    if restored_order:
                        _logger.info(f"Orden encontrada: {restored_order.name}")
                        
                        # Actualizar la orden con el usuario autenticado
                        restored_order.sudo().write({
                            'user_id': user.id,
                            'partner_id': user.partner_id.id
                        })
                        _logger.info(f"Orden actualizada con usuario: {restored_order.name}")
                        
                        # Verificar que el carrito se restauró correctamente
                        current_order = request.website.sale_get_order()
                        if current_order and current_order.id == cart_order_id:
                            _logger.info("✅ Carrito restaurado correctamente")
                        else:
                            _logger.warning("⚠️ Carrito no se restauró correctamente")
                    else:
                        _logger.error(f"❌ No se pudo encontrar la orden: {cart_order_id}")
                else:
                    _logger.warning("⚠️ No hay carrito para restaurar")
                
                # Commit final
                request.env.cr.commit()
                _logger.info("Transacción final confirmada")
                
                # Verificar que el usuario está realmente autenticado
                _logger.info(f"request.env.user.name: {request.env.user.name}")
                _logger.info(f"request.env.user.id: {request.env.user.id}")
                
                if request.env.user.id == user.id:
                    _logger.info("Usuario autenticado correctamente")
                    _logger.info("Redirigiendo a /shop/payment")
                    return request.redirect('/shop/payment')
                else:
                    _logger.warning("Usuario no autenticado en el entorno")
                    return self._fallback_native_authentication(user, email, password, order)
            else:
                _logger.error("No se pudo establecer la sesión")
                return self._fallback_native_authentication(user, email, password, order)
                
        except Exception as e:
            _logger.error(f"Error en autenticación directa: {str(e)}")
            return self._fallback_native_authentication(user, email, password, order)

    def _fallback_native_authentication(self, user, email, password, order):
        """ Método de fallback para autenticación nativa """
        try:
            _logger.info("🔄 OPCIÓN 3: Fallback de autenticación nativa...")
            
            # PRESERVAR EL CARRITO ANTES DE LA AUTENTICACIÓN
            cart_order_id = None
            if order:
                cart_order_id = order.id
                _logger.info(f"Preservando carrito: {order.name} (ID: {cart_order_id})")
            
            # Intentar autenticación manual usando el método de Odoo
            _logger.info("Intentando autenticación manual...")
            
            # Usar el método de autenticación del modelo de usuario (CORREGIDO: solo 4 argumentos)
            try:
                # CORREGIDO: Usar solo 4 argumentos como espera el método authenticate del modelo
                _logger.info(f"🔄 Intentando autenticación manual con modelo de usuario...")
                
                uid = user.sudo().authenticate(request.db, email, password, request.env)
                _logger.info(f"Autenticación manual exitosa: {uid}")
                
                if uid and uid == user.id:
                    # Establecer la sesión manualmente
                    request.session.uid = uid
                    request.session.login = user.login
                    request.session.db = request.db
                    
                    _logger.info(f"✅ Sesión manual establecida para usuario: {user.name}")
                    
                    # RESTAURAR EL CARRITO
                    if cart_order_id:
                        _logger.info(f"🔄 Restaurando carrito en fallback: {cart_order_id}")
                        request.session['sale_last_order_id'] = cart_order_id
                        
                        # Buscar y actualizar la orden
                        restored_order = request.env['sale.order'].sudo().browse(cart_order_id).exists()
                        if restored_order:
                            restored_order.sudo().write({
                                'user_id': uid,
                                'partner_id': user.partner_id.id
                            })
                            _logger.info(f"Orden actualizada en fallback: {restored_order.name}")
                    
                    # Commit final
                    request.env.cr.commit()
                    _logger.info("✅ Transacción final confirmada")
                    
                    _logger.info("✅ OPCIÓN 3: Redirigiendo a /shop/payment después de fallback nativo")
                    return request.redirect('/shop/payment')
                else:
                    _logger.error("❌ Autenticación manual falló")
                    return self._final_native_attempt(user, email, password, order)
                    
            except Exception as manual_error:
                _logger.error(f"Error en autenticación manual: {str(manual_error)}")
                return self._final_native_attempt(user, email, password, order)
                
        except Exception as e:
            _logger.error(f"Error en fallback nativo: {str(e)}")
            return self._final_native_attempt(user, email, password, order)

    def _final_native_attempt(self, user, email, password, order):
        """ Método final para autenticación nativa """
        try:
            _logger.info("🔄 OPCIÓN 3: Método final nativo...")
            
            _logger.info(f"✅ Usuario {user.name} creado y activado exitosamente")
            _logger.info(f"✅ Email: {email}")
            _logger.info(f"✅ Contraseña: ***")
            _logger.info(f"✅ Usuario activo: {user.active}")
            _logger.info(f"✅ Redirigiendo a login para autenticación manual")
            
            # Redirigir a la página de login con mensaje de éxito
            return request.redirect('/web/login?redirect=/shop/payment&registration=success&user_created=true')
                
        except Exception as e:
            _logger.error(f"Error en método final nativo: {str(e)}")
            return request.redirect('/web/login?redirect=/shop/payment&error=native_error')


    @http.route('/shop/get_payment_provider_carriers', type='json', auth='public', website=True)
    def get_payment_provider_carriers(self, provider_id):
        """
        Endpoint seguro para obtener los carriers asociados a un payment provider
        """
        try:
            if not provider_id:
                return {'success': False, 'message': 'Provider ID requerido'}
            
            # Obtener el payment provider de forma segura
            provider = request.env['payment.provider'].sudo().browse(int(provider_id)).exists()
            if not provider:
                return {'success': False, 'message': 'Provider no encontrado'}
            
            # Obtener los carriers asociados
            carriers = provider.delivery_carrier_ids
            carrier_ids = [carrier.id for carrier in carriers]
            
            return {
                'success': True,
                'carrier_ids': carrier_ids,
                'count': len(carrier_ids)
            }
            
        except Exception as e:
            return {'success': False, 'message': str(e)}


class CustomerPortalCustom(WebsiteSale):
    # tu código aquí

    def can_skip_delivery_step(self, order, delivery_methods):
        """
        Devuelve True si el pedido no tiene productos entregables,
        o False si requiere paso de entrega.
        """
        return not order._has_deliverable_products()


# Comentamos temporalmente el controlador de login para evitar conflictos
# class LoginController(Home):
#     """ Controlador personalizado para manejar login después del registro """
#     
#     @http.route('/web/login', type='http', auth='public', website=True, sitemap=False)
#     def web_login(self, redirect=None, **kw):
#         """ Sobrescribir el login para manejar registro exitoso """
#         try:
#             # Verificar si hay registro exitoso en la sesión
#             if request.session.get('registration_success'):
#                 _logger.info("=== DETECTADO REGISTRO EXITOSO EN LOGIN ===")
#                 
#                 # Obtener credenciales de la sesión
#                 email = request.session.get('registered_email')
#                 password = request.session.get('registered_password')
#                 redirect_url = request.session.get('redirect_after_login', '/shop/payment')
#                 
#                 _logger.info(f"Credenciales encontradas: email={email}, redirect={redirect_url}")
#                 
#                 if email and password:
#                     try:
#                         # Intentar autenticación automática
#                         _logger.info("Intentando autenticación automática...")
#                         uid = request.session.authenticate(request.db, email, password)
#                         
#                         if uid and uid != request.env.ref('base.public_user').id:
#                             _logger.info(f"✅ Autenticación automática exitosa: {email} (UID: {uid})")
#                             
#                             # Limpiar datos de sesión
#                             request.session.pop('registration_success', None)
#                             request.session.pop('registered_email', None)
#                             request.session.pop('registered_password', None)
#                             request.session.pop('redirect_after_login', None)
#                             
#                             # Redirigir al usuario
#                             _logger.info(f"✅ Redirigiendo a: {redirect_url}")
#                             return request.redirect(redirect_url)
#                         else:
#                             _logger.warning("Autenticación automática falló, mostrando formulario de login")
#                     except Exception as auth_error:
#                         _logger.error(f"Error en autenticación automática: {str(auth_error)}")
#                 
#                 # Limpiar datos de sesión si hay error
#                 request.session.pop('registration_success', None)
#                 request.session.pop('registered_email', None)
#                 request.session.pop('registered_password', None)
#                 request.session.pop('redirect_after_login', None)
#             
#             # Continuar con el login normal
#             return super().web_login(redirect=redirect, **kw)
#             
#         except Exception as e:
#             _logger.error(f"Error en web_login personalizado: {str(e)}")
#             return super().web_login(redirect=redirect, **kw)
