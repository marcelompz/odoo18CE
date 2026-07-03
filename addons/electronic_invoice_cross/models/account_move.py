# -*- coding: utf-8 -*-
"""
Modified on 2025-02-21 23:17:26

@author: drojo
"""
# python
from datetime import datetime, date, time
from base64 import b64decode  # base64 to pdf
import pytz  # timezone
import requests  # api
import json  # json format
import codecs  # bytes to xml
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .jsongenerator import create_json_data

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

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
        string='Comprobante fiscal', default=True)
    authorization_id = fields.Many2one(
        string='Timbrado', comodel_name='account.authorization', domain='[("active","=",True)]', copy=False)
    invoice_number = fields.Char(
        string='Número', copy=False)
    invoice_line_count = fields.Integer(
        string='Número de líneas', compute='_compute_lines_count')
    amount_subtotal_exempt = fields.Float(
        string='Subtotal exenta', compute='_compute_subtotals')
    amount_subtotal_5 = fields.Float(
        string='Subtotal 5%', compute='_compute_subtotals')
    amount_subtotal_10 = fields.Float(
        string='Subtotal 10%', compute='_compute_subtotals')
    amount_iva_5 = fields.Float(
        string='IVA 5%', compute='_compute_iva')
    amount_iva_10 = fields.Float(
        string='IVA 10%', compute='_compute_iva')
    amount_iva_total = fields.Float(
        string='Total IVA', compute='_compute_iva')
    amount_total_words = fields.Char(
        string='Total en letras', compute='_compute_amount_total_words')
    l10n_py_ids = fields.One2many(
        'account.l10n.py', 'account_id', string='ED-PY líneas')
    is_ed = fields.Boolean(
        string='Es un documento electrónico?', default=False, copy=False)
    client_eligible_de = fields.Boolean(
        related='partner_id.client_eligible_de')
    pdf_show = fields.Binary(
        string='PDF', copy=False)
    de_requested = fields.Boolean(
        string='DE solicitado?', compute='_compute_de_requested')
    is_ed_cancelled = fields.Boolean(
        string='Es un DE cancelado?', default=False, copy=False)
    de_status = fields.Selection(
        selection=de_status, string='Estado del DE', copy=False)
    response_code = fields.Char(
        string='Código de la Respuesta de la SET', copy=False)
    response_message = fields.Char(
        string='Mensaje de Respuesta de la SET', copy=False)
    creditdebit_note_id = fields.Many2one(
        'res.credit.debit.note', string='Motivo de la emisión')
    associated_document = fields.Char(
        string="Documento asociado")
    comes_from_invoice = fields.Boolean(
        string='Proviene de la factura', compute='_compute_comes_from_invoice')
    doc_format_id = fields.Many2one(
        'res.document.format', string='Formato del documento')
    doc_format_type_id = fields.Many2one(
        'res.document.format.type', string='Tipo de formato de documento')
    doc_stamped = fields.Char(
        string='Timbrado')
    doc_establishment = fields.Char(
        string='Establecimiento', size=3)
    doc_point = fields.Char(
        string='Punto', size=3)
    doc_number = fields.Char(
        string='Número', size=7)
    doc_date = fields.Date(
        string='Fecha')
    is_digital_certificate_expired = fields.Boolean(
        string='¿El certificado digital está caducado?', compute='_compute_is_digital_certificate_expired')
    cdc_l10n_py = fields.Char(
        string='Código de control (CDC)', compute='_compute_cdc_l10n_py')
    l10n_py_enabled_invoice_number = fields.Boolean(
        string='Habilitar número de factura', related='company_id.l10n_py_enabled_invoice_number')
    pre_printed_invoice = fields.Boolean(
        related='authorization_id.pre_printed_invoice')
        
    @api.depends('l10n_py_ids')
    def _compute_cdc_l10n_py(self):
        for record in self:
            record.cdc_l10n_py = False
            for line in record.l10n_py_ids: 
                if line.name and len(line.name) == 44:
                    record.cdc_l10n_py = line.name

    @api.depends('name')
    def _compute_is_digital_certificate_expired(self):
        for record in self:
            record.is_digital_certificate_expired = False

            if record.company_id.digital_certificate_expiration:
                if (record.company_id.digital_certificate_expiration - fields.Date.today()).days <= 10:
                    record.is_digital_certificate_expired = True
    
    @api.depends('associated_document')
    def _compute_comes_from_invoice(self):
        for rec in self:
            rec.comes_from_invoice = True if rec.associated_document else False
    
    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        stamped = False

        if res.get('move_type') == 'out_invoice':
            for authorization in self.env.user.authorization_ids:
                if authorization.latam_doc_type_id.code == '1': stamped = authorization
            
            if not stamped:
                stamped = self.env['account.authorization'].search([('latam_doc_type_id.code','=',1)], order='id desc', limit=1)
            
        elif res.get('move_type') == 'out_refund':
            for authorization in self.env.user.authorization_ids:
                if authorization.latam_doc_type_id.code == '5': stamped = authorization
            
            if not stamped:
                stamped = self.env['account.authorization'].search([('latam_doc_type_id.code','=',5)], order='id desc', limit=1)
        
        res.update({
            'authorization_id': stamped.id if stamped else False,
        })

        return res

    @api.depends('l10n_py_ids')
    def _compute_de_requested(self):
        for rec in self:
            rec.de_requested = True if (len(rec.l10n_py_ids) > 0 and rec.l10n_py_ids[0].ed_status != 'refused') else False

    @api.depends("amount_total")
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(
                invoice.amount_total
            )

    @api.model
    @api.depends("invoice_line_ids")
    def _compute_subtotals(self):
        for r in self:
            r.amount_subtotal_exempt = r.amount_subtotal_5 = r.amount_subtotal_10 = 0
            for l in r.invoice_line_ids:
                if l.tax_ids:
                    if l.tax_ids.amount == 0:
                        r.amount_subtotal_exempt += l.price_total
                    elif l.tax_ids.amount == 5:
                        r.amount_subtotal_5 += l.price_total
                    elif l.tax_ids.amount == 10:
                        r.amount_subtotal_10 += l.price_total
                else:
                    r.amount_subtotal_exempt += l.price_total

    @api.model
    @api.depends("invoice_line_ids")
    def _compute_iva(self):
        for r in self:
            r.amount_iva_5 = r.amount_iva_10 = 0
            for l in r.invoice_line_ids:
                if l.tax_ids:
                    if l.tax_ids.amount == 5:
                        r.amount_iva_5 += l.price_total - l.price_subtotal
                    elif l.tax_ids.amount == 10:
                        r.amount_iva_10 += l.price_total - l.price_subtotal
            r.amount_iva_total = r.amount_iva_5 + r.amount_iva_10

    @api.model
    @api.depends("invoice_line_ids")
    def _compute_lines_count(self):
        for record in self:
            record.invoice_line_count = len(record.invoice_line_ids)

    def action_post(self):
        # Valida que tenga un plazo de pago seleccionado
        if not self.invoice_payment_term_id and self.move_type == 'out_invoice':
            raise UserError(f'Debes seleccionar un Plazo de pago!')

        # Asigna el número de factura solo si es timbrado pre impreso y si el campo invoice_number esta vacio
        for rec in self:
            if rec.authorization_id.pre_printed_invoice and not rec.invoice_number:
                if (rec.move_type in ['out_invoice', 'out_refund'] and rec.fiscal_document):
                    auth = rec.authorization_id
                    number = "%s-%s-%s" % (
                        auth.establishment_code,
                        auth.generation_point,
                        f"{auth.next_number:07}",
                    )
                    rec.invoice_number = number
                    auth.write({"next_number": auth.next_number + 1})

        return super().action_post()

    def assign_number(self):
        for rec in self:
            if (
                rec.state == "posted"
                and rec.move_type in ['out_invoice', 'out_refund']
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

    def _get_cross_configurator(self, company=False):

        company = company or self.company_id
    
        url_api = company.url_api_cross
        api_key = company.api_key_cross
        sync_communication = company.sync_communication_cross

        return {
            "url_api": url_api,
            "api_key": api_key,
            "sync_communication": sync_communication,
        }

    def _get_current_datetime(self):
        """gets the current time of the zone

        Returns:
            datetime: invoice date & timezone time
        """
        invoice_date = (
            datetime.combine(self.invoice_date, datetime.min.time())
            if self.invoice_date
            else datetime.now()
        )
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        time_tz = datetime.now(tz=tz).time()
        return datetime.combine(invoice_date, time_tz)

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

    def send_json_to_set(self):
        params = self._get_cross_configurator()
        if params["sync_communication"]:
            # try:
            url = params["url_api"] + "/lote/create"
            headers = {
                "Authorization": f'Bearer api_key_{params["api_key"]}',
                "Content-Type": "application/json; charset=utf-8",
            }
            data = create_json_data(self)
            result = requests.post(url=url, verify=False, headers=headers, data=json.dumps(data))
            res_json = result.json()

            if result.status_code == 200:
                if res_json['success'] == True:
                    for delist in res_json["result"]["deList"]:
                        self.l10n_py_ids = [
                            (
                                0,
                                0,
                                {
                                    "name": delist["cdc"],
                                    "ed_status": "approved",
                                    "invoice_number": delist["numero"],
                                    "ed_xml": self.get_xml_to_save(cdc=delist["cdc"]),
                                    "json_result": res_json
                                },
                            )
                        ]

                    self.is_ed = True
                    self.message_post(body=_("Factura electrónica generada!!"))
                    self.get_de_status()
                    self.get_pdf_to_print()
                    self.env.user.cross_user_notify(message='Factura electrónica generado exitosamente!', reload=True)

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
                    logging.info("Error al intentar generar la factura electrónica\n%s:\n%s" % (main_error, formatted_errors))
                    self.message_post(body=_("Error al intentar generar la factura electrónica\n%s:\n%s" % (main_error, formatted_errors)))
                    
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
                self.l10n_py_ids = [
                    (
                        0,
                        0,
                        {
                            "ed_status": "refused",
                            "json_result": res_json
                        },
                    )
                ]
                return self.env.user.cross_user_notify(state='warning', message=result.status_code, reload=False, sticky=True)

        else:
            raise UserError(f"La comunicación sincrónica no está activa.")

    def get_pdf_to_print(self):
        params = self._get_cross_configurator()
        try:
            url = params["url_api"] + "/de/pdf"
            headers = {
                "Authorization": f'Bearer api_key_{params["api_key"]}',
                "Content-Type": "application/json; charset=utf-8",
            }

            data = {
                "cdcList": [{"cdc": self.cdc_l10n_py}],
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

                # Buscar mensajes relacionados con la factura
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

                self.message_post(body=_("Se obtuvo el PDF de la factura electrónica"), attachment_ids=attachment.ids)

            else:
                raise UserError(f'error 430: {result}')

        except ValidationError as e:  # Capturar primero ValidationError
            raise UserError(_(f"error nuevo: {e}"))

        except Exception as e:  # Capturar cualquier otro error
            raise UserError(_(f"error 611: {e}"))

    def get_xml_to_save(self, cdc=None):
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
            raise UserError(_(f"error 424: {e}"))

    def cancel_document_electronic(self):
        view_id = self.env.ref('electronic_invoice_cross.res_cancel_document_wizard_form')
            
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
                    'name': self.cdc_l10n_py,
                    'account_id': self.id,
                    'origin': 'account'
                },
            }
            
            return details_wiz_data

    def get_de_status(self):
        if self.is_ed:
            return self._get_de_status(reg=self, show_notification=True)
            
        else:
            # En caso de no encontrar la factura consultada en la SET
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Factura electrónica inexistente!'),
                    'type': 'danger',
                    'sticky': False,
                },
            }

    def cron_action_de_status(self):
        companies = self.env['res.company'].search([])

        for company in companies:
            invoices = self.env['account.move'].search([
                ('is_ed', '=', True),                                   # es factura electronica?
                ('move_type', 'in', ['out_invoice', 'out_refund']),     # es una venta o nota de credito?
                ('company_id', '=', company.id),                        # filtra por compañia
                ('de_status', '=', '0'),                                # estado DE = Generado DE
            ])

            for invoice in invoices:
                self._get_de_status(reg=invoice, company=company)

            _logger.info(f'''
                Se procesaron {len(invoices)} facturas electrónicas de la compañia {company.name}
            ''')

    def _get_de_status(self, reg, show_notification=False, company=False):
        params = self._get_cross_configurator(company=company)
        reg = reg
        try:
            url = params["url_api"] + "/de/estado"
            headers = {
                "Authorization": f'Bearer api_key_{params["api_key"]}',
                "Content-Type": "application/json; charset=utf-8",
            }

            data = {"cdcList": [{"cdc": reg.cdc_l10n_py}],}
            result = requests.post(url=url, verify=False, headers=headers, data=json.dumps(data))
            res_json = result.json()
                
            if result.status_code == 200:
                if res_json['success'] == True:
                    self.de_requested = True

                    for delist in res_json["deList"]:
                        reg.de_status = str(delist['situacion'])
                        reg.response_code = delist['respuesta_codigo']
                        reg.response_message = delist['respuesta_mensaje']

                        if reg.de_status == '2':
                            reg.is_ed_cancelled = False
                        
                        if delist['situacion'] == 4 and len(reg.l10n_py_ids) > 0:
                            reg.l10n_py_ids[0].ed_status = 'refused'

                        # Mostrar notificación solo si show_notification es True
                        if show_notification:
                            self.message_post(body=_("Consulta del estado de la factura electrónica en la SET"))
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _('Consulta exitosa!'),
                                    'type': 'success',
                                    'sticky': False,
                                },
                            }

            else:
                raise UserError(f'error 672: {result}')

        except Exception as e:
            raise UserError(_(f"error 675: {e}"))

    def send_json_to_set_again(self):
        if self.de_status == '4':
            self.pdf_show = False
            self.l10n_py_ids.unlink()
            self.send_json_to_set()


class AccountL10nPy(models.Model):
    _name = 'account.l10n.py'
    _description = 'ED result registration'

    _ed_status = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('refused', 'Refused'),
        ('approved', 'Approved'),
    ]

    name = fields.Char(
        string='CDC', readonly=True)
    ed_status = fields.Selection(
        string='ED status', readonly=True, selection=_ed_status)
    ed_error_code = fields.Char(
        string='ED error code', readonly=True)
    invoice_number = fields.Char(
        string='Invoice number', readonly=True)
    ed_xml = fields.Html(
        string='XML', readonly=True)
    account_id = fields.Many2one(
        'account.move', string='Account', readonly=True)
    json_result = fields.Text(
        string='Resultado del json')
