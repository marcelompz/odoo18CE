# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:32:30

@author: drojo
"""
# python
from datetime import datetime
import pytz  # timezone
import requests  # api
import json  # json format
import codecs  # bytes to xml
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from .jsongenerator import create_json_data

_logger = logging.getLogger(__name__)


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    _freight_cost = [
        ('1','Emisor de la Factura Electrónica'),
        ('2','Receptor de la Factura Electrónica'),
        ('3','Tercero'),
        ('4','Agente intermediario del transporte (cuando intervenga)'),
        ('5','Transporte propio'),
    ]
    de_status = [
        ('-1', 'Borrador'),
        ('0', 'Generado DE'),
        ('1', 'Enviado en un Lote'),
        ('2', 'Aprobado'),
        ('3', 'Aprobado con observacion'),
        ('4', 'Rechazado'),
        ('98', 'Inexistente'),
        ('99', 'Cancelado'),
    ]

    fiscal_document = fields.Boolean(
        string='Comprobante fiscal', default=False, tracking=True, copy=False)
    authorization_id = fields.Many2one(
        string='Timbrado', comodel_name='account.authorization', domain='[("active","=",True)]', tracking=True)
    invoice_number = fields.Char(
        string='Número', tracking=True, copy=False)
    client_eligible_de = fields.Boolean(
        related='partner_id.client_eligible_de')
    delivery_note_id = fields.Many2one(
        'res.delivery.note', string='Motivo de la nota de remisión', tracking=True)
    responsible_note_id = fields.Many2one(
        'res.delivery.responsible', string='Responsable de la nota de remisión', help='Responsable de la emisión de la Nota Remisión Electrónica', tracking=True)
    kms_traveled = fields.Integer(
        string='Estimación de kilómetros de recorrido', tracking=True)
    fleet_id = fields.Many2one(
        'fleet.vehicle', string='Transporte', tracking=True)
    driver_id = fields.Many2one(
        'res.partner', string='Conductor', tracking=True)
    transporte_type = fields.Selection(
        related='fleet_id.transport_type', tracking=True)
    fleet_modality = fields.Selection(
        related='fleet_id.modality', tracking=True)
    freight_cost = fields.Selection(
        string='Responsable del costo del flete', selection=_freight_cost, default='1', tracking=True)
    negotiation_condition_id = fields.Many2one(
        'res.negotiation.condition', string='Condición de la negociación', tracking=True)
    cross_carrier_id = fields.Many2one(
        related='fleet_id.cross_carrier_id', tracking=True)
    l10n_py_ids = fields.One2many(
        'stock.l10n.py', 'stock_id', string='Líneas de documentos de DE-PY', tracking=True, copy=False)
    is_ed = fields.Boolean(
        string='Es un documento electrónico?', default=False, copy=False)
    pdf_show = fields.Binary(
        string='PDF', copy=False)
    end_transfer_date = fields.Datetime(
        string='Fecha fin de transferencia', default=fields.Datetime().now(), tracking=True)
    is_ed_cancelled = fields.Boolean(
        string='¿Se cancela el documento electrónico?', default=False)
    de_status = fields.Selection(
        selection=de_status, string='Estado del DE', tracking=True, copy=False)
    response_code = fields.Char(
        string='Código de la Respuesta de la SET', tracking=True, copy=False)
    response_message = fields.Char(
        string='Mensaje de Respuesta de la SET', tracking=True, copy=False)
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', domain=[('res_model', '=', 'stock.picking')], string='Attachments')

    @api.onchange('picking_type_code')
    def onchange_picking_type_code(self):
        if self.picking_type_code == 'internal' or self.picking_type_code == 'outgoing':
            stamped = self.env['account.authorization'].search([('latam_doc_type_id.code','=',7)], order='id desc', limit=1)

            if stamped:
                self.authorization_id = stamped.id
                self.fiscal_document = True

    def _get_cross_configurator(self):
        url_api = self.company_id.url_api_cross
        api_key = self.company_id.api_key_cross
        sync_communication = self.company_id.sync_communication_cross

        return {
            "url_api": url_api,
            "api_key": api_key,
            "sync_communication": sync_communication,
        }

    def electronic_invoice_action(self):
        self.assign_number()
        params = self._get_cross_configurator()
        
        if params["sync_communication"]:
            url = params["url_api"] + "/lote/create"
            headers = {
                "Authorization": f'Bearer api_key_{params["api_key"]}',
                "Content-Type": "application/json; charset=utf-8",
            }
            data = create_json_data(self, origin='stock')
            result = requests.post(url=url, verify=False, headers=headers, data=json.dumps(data))
            res_json = result.json()

            if result.status_code == 200:
                if res_json['success'] == True:
                    for delist in res_json["result"]["deList"]:
                        self.l10n_py_ids = [(0,0,{
                            "name": delist["cdc"],
                            "ed_status": "approved",
                            "invoice_number": delist["numero"],
                            "ed_xml": self._get_xml(cdc=delist["cdc"]),
                            "json_result": res_json
                        },)]

                    self.is_ed = True
                    self.message_post(body=_("Remisión electrónica generada!!"))
                    self._get_pdf()
                    return self.env.user.cross_user_notify(message='Nota de remisión electrónica generado exitosamente!', reload=True)

                else:
                    # Obtener el título del 'error'
                    main_error = res_json.get('error', '')

                    # Obtener el detalle del 'error' y separarlo por ';'
                    nested_errors_raw = [e.get('error', '') for e in res_json.get('errores', [])]
                    nested_errors = []

                    # Dividir cada error por ';' y agregarlo a la lista de errores
                    for raw_error in nested_errors_raw:
                        nested_errors.extend([f" *** {err.strip()}" for err in raw_error.split(';') if err.strip()])

                    # Unir los errores con saltos de línea
                    formatted_errors = "\n".join(nested_errors)

                    # Registrar el error en el mensaje
                    logging.info("Error al intentar generar la remisión electrónica\n%s:\n%s" % (main_error, formatted_errors))
                    self.message_post(body=_("Error al intentar generar la remisión electrónica\n%s:\n%s" % (main_error, formatted_errors)))
                    
                    self.l10n_py_ids = [(0,0,{
                        "ed_status": "refused",
                        "ed_error_code": "ERROR",
                        "json_result": res_json
                    },)]

                    if res_json['errores']:
                        for error_line in res_json['errores']:
                            return self.env.user.cross_user_notify(state='warning', message=error_line['error'], reload=False, sticky=True)

                    else:
                        return self.env.user.cross_user_notify(state='warning', message='Error no descripto.', reload=False, sticky=True)

            else:
                self.l10n_py_ids = [(0,0,{
                    "ed_status": "refused",
                    "json_result": res_json
                },)]

                return self.env.user.cross_user_notify(state='warning', message=result.status_code, reload=False, sticky=True)

        else:
            raise UserError(f"La comunicación sincrónica no está activa.")

    def _get_current_datetime(self):
        """gets the current time of the zone

        Returns:
            datetime: invoice date & timezone time
        """
        date_done = (
            datetime.combine(self.date_done, datetime.min.time())
            if self.date_done
            else datetime.now()
        )
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        time_tz = datetime.now(tz=tz).time()
        return datetime.combine(date_done, time_tz)

    def _get_type_of_operations(self):
        """obtains the type of operations according to conditions

        Returns:
            int: operation type
        """
        if self.partner_id.l10n_latam_identification_type_id.document_id == 0:
            res = 1  # B2B
        elif self.partner_id.l10n_latam_identification_type_id.document_id == 1:
            res = 2  # B2C

        if self.partner_id.is_a_state_provider:
            res = 3  # B2G

        if self.partner_id.l10n_latam_identification_type_id.document_id == 3:
            res = 4  # B2F

        return res

    def assign_number(self):
        for rec in self:
            if (
                rec.state == "done"
                and (rec.picking_type_code == "internal" or rec.picking_type_code == 'outgoing')
                and rec.fiscal_document
                and not rec.invoice_number
            ):
                auth = rec.authorization_id
                number = "%s-%s-%s" % (
                    auth.establishment_code,
                    auth.generation_point,
                    f"{auth.next_number:07}",
                )
                rec.invoice_number = number
                auth.write({"next_number": auth.next_number + 1})

    def _get_pdf(self):
        params = self._get_cross_configurator()
        cdc = False
        try:
            url = params["url_api"] + "/de/pdf"
            headers = {
                "Authorization": f'Bearer api_key_{params["api_key"]}',
                "Content-Type": "application/json; charset=utf-8",
            }

            for line in self.l10n_py_ids: 
                if line.name and len(line.name) == 44:
                    cdc = line.name

            data = {
                "cdcList": [{"cdc": cdc}],
                "type": "base64",
            }

            result = requests.post(
                url=url, verify=False, headers=headers, data=json.dumps(data)
            )

            if result.status_code == 200:
                pdf_base64 = result.content
                self.pdf_show = pdf_base64

                self.attachment_ids.unlink()
                attachment_id = self.env['ir.attachment'].search([
                    ('res_model', '=', 'mail.message'),
                    ('name', 'ilike', self.name),
                ])

                if attachment_id: attachment_id.unlink()

                # Buscar mensajes relacionados con la remisión
                messages = self.env['mail.message'].search([
                    ('model', '=', 'account.move'),
                    ('res_id', '=', self.id)
                ])

                # Buscar y eliminar los adjuntos vinculados a los mensajes
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'mail.message'),
                    ('res_id', 'in', messages.ids)
                ])

                if attachments: attachments.unlink()

                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.invoice_number}.pdf",
                    'description': f"{self.invoice_number}.pdf",
                    'res_model': self._name,
                    'res_id': self.id,
                    'type': 'binary',
                    'public': False,
                    'datas': pdf_base64,
                })

                self.message_post(body=_("Se obtuvo el PDF de la remisión electrónica"), attachment_ids=attachment.ids)

            else:
                raise UserError(f'error 415: {result}')

        except Exception as e:
            raise UserError(_(f"error 422: {e}"))

    def _get_xml(self, cdc=None):
        params = self._get_cross_configurator()
        headers = {"Authorization": f'Bearer api_key_{params["api_key"]}'}
        try:
            if cdc != None:
                url = params["url_api"] + "/de/xml/" + cdc + "?json=false"
                result = requests.get(url=url, verify=False, headers=headers)

                if result.status_code == 200:
                    return codecs.decode(result.content, "UTF-8")

            else:
                for ed_line in self.l10n_py_ids:
                    if ed_line.name:
                        url = (
                            params["url_api"] + "de/xml/" + ed_line.name + "?json=false"
                        )
                        result = requests.get(url=url, verify=False, headers=headers)

                        if result.status_code == 200:
                            return codecs.decode(result.content, "UTF-8")

            return False

        except Exception as e:
            raise UserError(_(f"error 445: {e}"))

    def _get_associated_document(self):
        document = []
        invoices = self.sale_id.mapped('invoice_ids')
        cdc = False

        for invoice in invoices:
            if invoice.is_ed:
                for line in invoice.l10n_py_ids: 
                    if line.name and len(line.name) == 44:
                        cdc = line.name

                document.append({'formato': 1, 'cdc': cdc})
                
        return document

    def get_pdf_from_fs(self):
        res = self._get_pdf()
        if res:
            return self.env.user.cross_user_notify(message='PDF de la Nota de remisión electrónica obtenido exitosamente!', reload=True)

    @api.constrains('fiscal_document', 'client_eligible_de', 'kms_traveled', 'picking_type_code', 'driver_id')
    def _check_condition_to_confirm(self):
        for rec in self:
            if rec.fiscal_document:
                if not rec.client_eligible_de:
                    raise ValidationError('La dirección de entrega y/o Contacto no está con los datos completos para obtener un documento electrónico.')

                if rec.kms_traveled <= 0:
                    raise ValidationError('El km estimado de recorrido debe ser mayor a cero.')

                driver = rec.driver_id
                if not driver.vat or not driver.name or not driver.street:
                    raise ValidationError('Faltan datos del conductor\nLos obligatorios son Nombre, cédula de identidad y dirección.')

                if rec.picking_type_code == 'internal':
                    destination = self.location_dest_id.warehouse_id.partner_id
                    if not destination.street or not destination.state_id or not destination.district_id or not destination.city_id or not destination.country_id or not destination.mobile:
                        raise ValidationError('Faltan datos de la ubicación del almacend de destino\nLos obligatorios son la dirección completa como calle, ciudad, distrito, departamento y país, como así también un número de celular.')

    def cancel_document_electronic(self):
        view_id = self.env.ref('electronic_invoice_cross.res_cancel_document_wizard_form')
        cdc = False

        for line in self.l10n_py_ids: 
                if line.name and len(line.name) == 44:
                    cdc = line.name
            
        if view_id:
            details_wiz_data = {
                'name': _('Cancelar documento electrónico'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'res.cancel.document.wizard',
                'target': 'new',
                'view_id': view_id.id,
                'context': {
                    'name': cdc,
                    'stock_id': self.id,
                    'origin': 'stock'
                },
            }
            
        return details_wiz_data

    def get_de_status(self):
        if self.is_ed:
            self._get_de_status(reg=self)
            
        else:
            return self.env.user.cross_user_notify(state='danger', message='Factura electrónica inexistente!', reload=False)

    def _get_de_status(self, reg):
        params = self._get_cross_configurator()
        cdc = False
        reg = reg

        try:
            url = params["url_api"] + "/de/estado"
            headers = {
                "Authorization": f'Bearer api_key_{params["api_key"]}',
                "Content-Type": "application/json; charset=utf-8",
            }

            for line in reg.l10n_py_ids: 
                if line.name and len(line.name) == 44:
                    cdc = line.name

            data = {"cdcList": [{"cdc": cdc}],}
            result = requests.post(url=url, verify=False, headers=headers, data=json.dumps(data))
            res_json = result.json()

            if result.status_code == 200:
                if res_json['success'] == True:
                    for delist in res_json["deList"]:
                        reg.de_status = str(delist['situacion'])
                        reg.response_code = delist['respuesta_codigo']
                        reg.response_message = delist['respuesta_mensaje']
                        
                        if delist['situacion'] == 4 and len(reg.l10n_py_ids) > 0:
                            reg.l10n_py_ids[0].ed_status = 'refused'

                        return self.env.user.cross_user_notify(message='Consulta exitosa!', reload=True)

            else:
                raise UserError(f'error 560: {result}')

        except Exception as e:
            raise UserError(_(f"error 563: {e}"))


class StockL10nPy(models.Model):
    _name = 'stock.l10n.py'
    _description = 'Registro del resultado del DE'

    _ed_status = [
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('refused', 'Rechazado'),
        ('approved', 'Aprobado'),
    ]

    name = fields.Char(
        string='CDC', readonly=True)
    ed_status = fields.Selection(
        string='Estado del DE', readonly=True, selection= _ed_status)
    ed_error_code = fields.Char(
        string='Código de error del DE', readonly=True)
    invoice_number = fields.Char(
        string='Número Factura', readonly=True)
    ed_xml = fields.Html(
        string='XML', readonly=True)
    stock_id = fields.Many2one(
        'stock.picking', string='Stock', readonly=True)
    json_result = fields.Text(
        string='Resultado del json')
