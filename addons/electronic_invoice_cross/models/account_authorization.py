# -*- coding: utf-8 -*-
"""
Modified on 2025-02-21 23:16:39

@author: drojo
"""
# python
import datetime

# odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging


_logger = logging.getLogger(__name__)


class Authorization(models.Model):
    _name = 'account.authorization'
    _description = 'Timbrado de la Administración Tributaria '
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(
        string="Nombre", required=True, tracking=True)
    stamped = fields.Char(
        string='Número', required=True, tracking=True)
    date_from = fields.Date(
        string="Desde", required=True, help="Fecha de autorización del timbrado", tracking=True)
    date_to = fields.Date(
        string="Hasta", required=True, help="Fecha límite de vigencia del timbrado", tracking=True)
    establishment_code = fields.Char(
        string="Código de establecimiento", required=True, size=3, tracking=True)
    generation_point = fields.Char(
        string="Punto de expedición", required=True, size=3, tracking=True)
    numbers_start = fields.Integer(
        string="Inicio de numeración", default=1, required=True, tracking=True)
    numbers_end = fields.Integer(
        string="Final de numeración", default=1000, required=True, tracking=True)
    next_number = fields.Integer(
        string="Siguiente número", required=True, default=1, tracking=True)
    active = fields.Boolean(
        string="Vigente", compute="_compute_active", store=True)
    company_id = fields.Many2one(
        'res.company', string='Empresa', required=True, readonly=True, default=lambda self: self.env.company)
    move_ids = fields.One2many(
        comodel_name="account.move", inverse_name="authorization_id", string="Facturas", copy=False)
    latam_doc_type_id = fields.Many2one(
        'l10n_latam.document.type', string='Documento relacionado')
    downtime_history_ids = fields.One2many(
        'account.authorization.downtime.history', 'authorization_id', string='Evento de inutilización')
    pre_printed_invoice = fields.Boolean(
        string='Es factura pre-impresa?', default=False)

    @api.depends('date_to')
    def _compute_active(self):
        for rec in self:
            if rec.date_to and rec.date_to >= datetime.date.today():
                rec.active = True
            else:
                rec.active = False

    @api.onchange('numbers_start')
    def _onchange_numbers_start(self):
        if self.next_number == 1 and self.numbers_start >= 1:
            self.next_number = self.numbers_start

    @api.constrains('next_number', 'numbers_start', 'numbers_end')
    def _check_next_number(self):
        for rec in self:
            if rec.next_number < 1 or rec.next_number < rec.numbers_start or rec.next_number > rec.numbers_end+1:
                raise ValidationError('Campo Siguiente número no válido.')

    @api.constrains('numbers_start', 'numbers_end')
    def _check_numbers_range(self):
        for rec in self:
            if rec.numbers_start <= 0 or rec.numbers_end <= 0 or rec.numbers_start > rec.numbers_end:
                raise ValidationError('Campos de rango de números no válidos.')

    @api.constrains('establishment_code', 'generation_point')
    def _check_codes(self):
        for rec in self:
            if not rec.establishment_code.isdigit() or not rec.generation_point.isdigit() \
                    or len(rec.establishment_code) != 3 or len(rec.generation_point) != 3:
                raise ValidationError('Campos Código de establecimiento y/o Punto de expedición no válido(s).')

    def disabling_event(self):
        """
        Abre una vista de formulario para el asistente de eventos de tiempo de inactividad.

        Este método recupera la vista de formulario definida por el ID XML
        'electronic_invoice_cross.de_downtime_event_wizard_form' y la abre
        como un cuadro de diálogo modal. Si no se encuentra la vista, el método devuelve un diccionario vacío.

        :return: Diccionario que contiene la acción para abrir el asistente o un diccionario vacío.
        :rtype: dict
        """
        # Fetch the view ID safely
        view_id = self.env.ref(
            'electronic_invoice_cross.de_downtime_event_wizard_form', 
            raise_if_not_found=False
        )
        
        # Default action to avoid returning an undefined variable
        details_wiz_data = {}
        
        if view_id:
            details_wiz_data = {
                'name': _('Evento de Inutilización'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'de.downtime.event.wizard',
                'target': 'new',
                'view_id': view_id.id,
            }
        
        return details_wiz_data



class AccountAuthorizationDowntimeHistory(models.Model):
    _name = 'account.authorization.downtime.history'
    _description = 'Historia del evento de inutilización'

    authorization_id = fields.Many2one(
        'account.authorization', string='Timbrado')
    latam_doc_type_id = fields.Many2one(
        related='authorization_id.latam_doc_type_id')
    establishment_code = fields.Char(
        related='authorization_id.establishment_code')
    generation_point = fields.Char(
        related='authorization_id.generation_point')
    number_from = fields.Integer(
        string='Número desde')
    number_to = fields.Integer(
        string='Número hasta')
    reason = fields.Text(
        string='Razón')
    json_sent = fields.Html(
        string='json enviado')
    state = fields.Selection(
        string='Estado', selection=[('refused', 'Rechazado'),('approved', 'Aprobado')])
    json_result = fields.Text(
        string='resultado json')
    json_message = fields.Char(
        string='Mensaje')
