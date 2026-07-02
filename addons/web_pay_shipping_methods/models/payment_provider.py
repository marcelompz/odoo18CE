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
from odoo import fields, models, api
from odoo.http import request
from odoo import http
import base64


class PaymentProvider(models.Model):
    """Inherited payment_provider to add shipping method field"""
    _inherit = 'payment.provider'

    delivery_carrier_ids = fields.Many2many(
        'delivery.carrier',
        string="Shipping Methods",
        domain="[('website_published', '=', True)]",
        help="Add shipping methods which will be available while"
             " choosing this payment provider")

    partner_ids = fields.Many2many(
        'res.partner',
        string="Direcciones asociadas",
        help="Direcciones asociadas a este proveedor de pago"
    )

    delivery_address_id = fields.Many2one(
        'res.partner',
        string="Dirección de Entrega",
        help="Dirección de entrega asociada a este proveedor de pago"
    )

    # Campos para adjuntos de comprobantes de transferencia
    transfer_receipt_attachment = fields.Binary(
        string='Comprobante de Transferencia',
        help='Comprobante de transferencia subido durante el proceso de pago'
    )
    transfer_receipt_name = fields.Char(
        string='Nombre del Comprobante',
        help='Nombre del archivo del comprobante de transferencia'
    )

    def _process_transfer_receipt_attachment(self, file_data, filename):
        """
        Procesa el comprobante de transferencia subido y lo guarda como comentario
        """
        if file_data and filename:
            # Guardar el archivo como attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': file_data,
                'res_model': 'payment.provider',
                'res_id': self.id,
                'type': 'binary',
            })
            
            # Agregar comentario al proveedor de pago
            comment = f"Comprobante de transferencia subido: {filename}"
            if hasattr(self, 'note') and self.note:
                self.note = f"{self.note}\n\n{comment}"
            else:
                # Si no existe el campo note, crear un mensaje en el chatter
                self.message_post(
                    body=comment,
                    attachment_ids=[attachment.id]
                )
                
            # Guardar referencia del archivo en los campos específicos
            self.transfer_receipt_attachment = file_data
            self.transfer_receipt_name = filename
            
            return attachment
        return False

    @api.model
    def create(self, vals):
        """
        Override create para procesar comprobantes de transferencia durante la creación
        """
        provider = super(PaymentProvider, self).create(vals)
        
        # Procesar comprobante de transferencia si existe
        if vals.get('transfer_receipt_attachment') and vals.get('transfer_receipt_name'):
            provider._process_transfer_receipt_attachment(
                vals['transfer_receipt_attachment'],
                vals['transfer_receipt_name']
            )
        
        return provider

    def write(self, vals):
        """
        Override write para procesar comprobantes de transferencia durante la actualización
        """
        result = super(PaymentProvider, self).write(vals)
        
        # Procesar comprobante de transferencia si existe
        if vals.get('transfer_receipt_attachment') and vals.get('transfer_receipt_name'):
            for provider in self:
                provider._process_transfer_receipt_attachment(
                    vals['transfer_receipt_attachment'],
                    vals['transfer_receipt_name']
                )
        
        return result

    def confirm_order(self, **post):
        order = request.website.sale_get_order()
        file = request.httprequest.files.get('bank_transfer_receipt')
        if file:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': file.filename,
                'datas': base64.b64encode(file.read()),
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': file.mimetype,
            })
            order.sudo().message_post(
                body="Comprobante de transferencia adjuntado por el cliente en el checkout.",
                attachment_ids=[attachment.id]
            )
        return request.redirect('/shop/confirmation')
