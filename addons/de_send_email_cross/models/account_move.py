# -*- coding: utf-8 -*-
"""
Created on 2025-03-13 17:52:40

@author: drojo
"""
# python
import logging
import base64
import dns.resolver

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    de_email_formatted_send = fields.Char(
        string='Correo electrónico para enviar DE', compute='_compute_de_email_formatted_send')
    email_sent = fields.Boolean(
        string='Email enviado', default=False, copy=False)
    
    @api.depends('partner_id')
    def _compute_de_email_formatted_send(self):
        mail_server = self.env['ir.mail_server'].sudo().search([('is_send_de', '=', True)], limit=1)

        for record in self:
            record.de_email_formatted_send = f'"{mail_server.name}" <{mail_server.smtp_user}>' if mail_server else False
    
    def action_send_email(self, show_notification=False):
        self.ensure_one()
        
        if not self.is_ed or not self.cdc_l10n_py:
            raise UserError('El documento no es electrónica o no fue generada aún!')

        partner = self.partner_id
        if not partner or not partner.email or not self._is_email_domain_valid(partner.email):
            self.message_post(body=_("El envío de correo fue omitido. Causa: Correo electrónico del cliente inválido o ausente (%s).") % partner.email if partner else "Cliente no asignado.")
            self.email_sent = False
            if show_notification:
                return self.env.user.cross_user_notify(state='warning', message='Email no enviado: correo del cliente inválido.', reload=False, sticky=True)
            return

        try:
            # Contenido del PDF en base64
            pdf_content = self.pdf_show

            # Contenido del XML
            xml_string = self.get_xml_to_save(cdc=self.cdc_l10n_py)
            if not xml_string:
                raise UserError("No se pudo generar el contenido del archivo XML.")
            
            # Convertir el XML a Base64
            xml_content = base64.b64encode(xml_string.encode("utf-8"))

            # 3. Preparar los adjuntos para el envío sin crear registros ir.attachment
            attachments_data = [
                (f'Factura_{self.invoice_number}.pdf', pdf_content),
                (f'XML_{self.invoice_number}.xml', xml_content),
            ]

            mail_template = self.env.ref('de_send_email_cross.send_de_by_email_cross')
            mail_server = self.env['ir.mail_server'].sudo().search([('is_send_de', '=', True)], limit=1)

            email_values = {
                # Odoo crea los adjuntos en el momento del envío con esta sintaxis
                'attachment_ids': [(0, 0, {'name': name, 'datas': datas, 'mimetype': 'application/octet-stream'}) for name, datas in attachments_data]
            }

            if self.company_id.email_to_copy_de:
                email_values['email_cc'] = self.company_id.email_to_copy_de
            
            if mail_server:
                email_values['mail_server_id'] = mail_server.id

            mail_template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

            self.email_sent = True
            if show_notification:
                self.env.user.cross_user_notify(message='Email enviado correctamente!', reload=True)

        except Exception as e:
            _logger.error("Error al enviar el correo de la factura %s: %s", self.name, e)
            self.message_post(body=_("Ocurrió un error al intentar enviar el correo electrónico: %s") % e)
            self.email_sent = False
            if show_notification:
                return self.env.user.cross_user_notify(state='danger', message=f'Error al enviar email: {e}', reload=False)

    def _has_mx_record(self, domain):
        try:
            records = dns.resolver.resolve(domain, 'MX')
            return len(records) > 0
        except Exception:
            return False

    def _is_email_domain_valid(self, email):
        domain = email.split('@')[-1]
        return self._has_mx_record(domain)

    def _action_create_invoice_attachment(self):
        self.ensure_one()
        
        if not self.pdf_show:
            return

        attachment_vals = {
            'name': f'Factura_{self.invoice_number}.pdf',
            'datas': self.pdf_show,
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        }
        attachment = self.env['ir.attachment'].create(attachment_vals)

        return attachment

    # def _create_xml_attachment(self):
    #     self.ensure_one()

    #     xml = self.get_xml_to_save(cdc=self.cdc_l10n_py)

    #     # Convertir el string a Base64
    #     xml_base64 = base64.b64encode(xml.encode("utf-8")).decode("utf-8")

    #     attachment_vals = {
    #         'name': f'XML_{self.invoice_number}.xml',
    #         'datas': xml_base64,  # Ahora en formato Base64
    #         'res_model': 'account.move',
    #         'res_id': self.id,
    #         'mimetype': 'application/xml',
    #     }
    #     attachment = self.env['ir.attachment'].create(attachment_vals)
        
    #     return attachment

    def _get_de_status(self, reg, show_notification=False, company=False):
        res = super()._get_de_status(reg, show_notification, company)

        if reg.pdf_show and not reg.email_sent and reg.invoice_date == fields.Date.context_today(self):
            reg.action_send_email()

        return res
