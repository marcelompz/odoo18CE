# -*- coding: utf-8 -*-
"""
Created on 2025-03-13 22:18:12

@author: drojo
"""
# python
import logging
import base64

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

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

        if not self.is_ed:
            raise UserError('La nota de remisión no es electrónica o no fue generada aún!')

        partner = self.partner_id
        if not partner or not partner.email:
            self.message_post(body=_("El envío de correo fue omitido. Causa: Correo electrónico del cliente inválido o ausente (%s).") % partner.email if partner else "Cliente no asignado.")
            self.email_sent = False
            if show_notification:
                return self.env.user.cross_user_notify(state='warning', message='Email no enviado: correo del cliente inválido.', reload=False, sticky=True)
            return

        try:

            # pdf_attachment = self.env['ir.attachment'].search([('res_model', '=', 'stock.picking'), ('res_id', '=', self.id)], limit=1)
            pdf_attachment = self.pdf_show
            
            if not pdf_attachment:
                pdf_attachment = self._action_create_invoice_attachment()
            # else:
            #     pdf_attachment = pdf_attachment.filtered(lambda a: a.name.startswith('NR_'))

            # Crear el archivo XML
            xml_attachment = self._create_xml_attachment()

            mail_template = self.env.ref('de_send_email_cross.send_nr_by_email_cross')
            mail_server = self.env['ir.mail_server'].sudo().search([('is_send_de', '=', True)], limit=1)

            # Preparar los adjuntos para el envío sin crear registros ir.attachment
            attachments_data = [
                (f'NR_{self.invoice_number}.pdf', pdf_attachment),
                (f'XML_{self.invoice_number}.xml', xml_attachment.datas),
            ]

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
                    return self.env.user.cross_user_notify(message='Email enviado correctamente', reload=True)

        except Exception as e:
            raise UserError(f'{e}')
            _logger.error("Error al enviar el correo de la factura %s: %s", self.name, e)
            self.message_post(body=_("Ocurrió un error al intentar enviar el correo electrónico: %s") % e)
            self.email_sent = False
            if show_notification:
                return self.env.user.cross_user_notify(state='danger', message=f'Error al enviar email: {e}', reload=False)

    def _action_create_invoice_attachment(self):
        self.ensure_one()
        
        if not self.pdf_show:
            return  # Asegúrate de que haya un PDF disponible

        attachment_vals = {
            'name': f'NR_{self.invoice_number}.pdf',
            'datas': self.pdf_show,
            'res_model': 'stock.picking',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        }
        attachment = self.env['ir.attachment'].create(attachment_vals)
        
        return attachment

    def _create_xml_attachment(self):
        self.ensure_one()

        # 1. Definimos el nombre esperado para el archivo
        #    Es importante definirlo una sola vez para usarlo en la búsqueda y en la creación.
        expected_name = f'XML_{self.invoice_number or self.name}.xml'

        # 2. Buscamos si ya existe un adjunto con ese nombre para este registro
        existing_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name), # Usar self._name es más robusto que 'stock.picking'
            ('res_id', '=', self.id),
            ('name', '=', expected_name),
        ], limit=1)

        # 3. Si encontramos un adjunto, simplemente lo devolvemos
        if existing_attachment:
            _logger.info("Adjunto XML '%s' ya existente encontrado para %s. Reutilizando.", expected_name, self.name)
            # Opcional: podrías actualizar su contenido si piensas que puede cambiar
            # xml_content = ...
            # existing_attachment.write({'datas': xml_content})
            return existing_attachment

        # 4. Si NO encontramos un adjunto, procedemos a crearlo (tu lógica original)
        _logger.info("Creando nuevo adjunto XML '%s' para %s.", expected_name, self.name)
        
        cdc = self.l10n_py_ids.filtered(lambda l: len(l.name) == 44).name
        xml_string = self._get_xml(cdc=cdc)
        if not xml_string:
            # Es buena práctica manejar el caso en que el XML no se pueda generar
            return self.env['ir.attachment']

        xml_base64 = base64.b64encode(xml_string.encode("utf-8")).decode("utf-8")

        attachment_vals = {
            'name': expected_name, # Usamos la variable que definimos al principio
            'datas': xml_base64,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/xml',
        }
        
        new_attachment = self.env['ir.attachment'].create(attachment_vals)
        
        return new_attachment

    def _get_de_status(self, reg):
        res = super()._get_de_status(reg)

        if reg.pdf_show and not reg.email_sent and reg.date_done == fields.Date.context_today(self):
            reg.action_send_email()

        return res
