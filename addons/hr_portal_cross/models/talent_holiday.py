# -*- coding: utf-8 -*-
"""Feriado visual con imagen y mensaje reflexivo.
Permite enviar un aviso a todos los empleados sobre el feriado."""
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TalentHoliday(models.Model):
    _name = 'talent.holiday'
    _description = 'Feriado (con imagen y mensaje)'
    _inherit = ['mail.thread']
    _order = 'date, id'
    _rec_name = 'name'

    name = fields.Char(string='Nombre del Feriado', required=True, tracking=True)
    date = fields.Date(string='Fecha', required=True, tracking=True, index=True)
    description = fields.Html(
        string='Descripcion',
        help='Origen, historia o significado del feriado.',
    )
    reflective_message = fields.Html(
        string='Mensaje Reflexivo',
        help='Mensaje que se enviara a todos los empleados.',
    )
    image = fields.Image(
        string='Imagen', max_width=1024, max_height=1024,
    )
    image_small = fields.Image(
        string='Imagen pequena', related='image', max_width=256, max_height=256,
        store=True,
    )
    is_national = fields.Boolean(string='Feriado Nacional', default=True)
    is_movable = fields.Boolean(
        string='Movible', default=False,
        help='Si es movible, la fecha puede ajustarse al lunes mas cercano segun ley.',
    )
    country_id = fields.Many2one(
        'res.country', string='Pais',
        default=lambda self: self.env.company.country_id,
    )
    color = fields.Selection([
        ('red', 'Rojo'), ('orange', 'Naranja'), ('green', 'Verde'),
        ('blue', 'Azul'), ('purple', 'Violeta'), ('pink', 'Rosa'),
    ], default='red', string='Color')
    notification_sent = fields.Boolean(
        string='Notificacion Enviada', readonly=True, copy=False,
    )
    notification_date = fields.Datetime(
        string='Fecha de Envio', readonly=True, copy=False,
    )

    days_until = fields.Integer(
        string='Dias restantes', compute='_compute_days_until',
    )
    is_past = fields.Boolean(
        string='Pasado', compute='_compute_days_until',
        search='_search_is_past',
    )
    is_today = fields.Boolean(
        string='Hoy', compute='_compute_days_until',
        search='_search_is_today',
    )

    @api.depends('date')
    def _compute_days_until(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.date:
                rec.days_until = 0
                rec.is_past = False
                rec.is_today = False
                continue
            delta = (rec.date - today).days
            rec.days_until = delta
            rec.is_past = delta < 0
            rec.is_today = delta == 0

    def _search_is_past(self, operator, value):
        today = fields.Date.context_today(self)
        if operator not in ('=', '!='):
            return []
        is_true = bool(value) if operator == '=' else not bool(value)
        if is_true:
            return [('date', '<', today)]
        return ['|', ('date', '=', False), ('date', '>=', today)]

    def _search_is_today(self, operator, value):
        today = fields.Date.context_today(self)
        if operator not in ('=', '!='):
            return []
        is_true = bool(value) if operator == '=' else not bool(value)
        if is_true:
            return [('date', '=', today)]
        return ['|', ('date', '=', False), ('date', '!=', today)]

    def action_send_notification(self):
        """Envia un mensaje interno a todos los empleados activos."""
        self.ensure_one()
        Employee = self.env['hr.employee']
        employees = Employee.search([
            ('active', '=', True),
            ('work_email', '!=', False),
        ])
        if not employees:
            employees = Employee.search([('active', '=', True)])
        if not employees:
            raise UserError(_('No hay empleados activos a quienes notificar.'))

        partners = employees.mapped('user_id.partner_id') | employees.mapped(
            'work_contact_id')
        partners = partners.filtered(lambda p: p)
        if not partners:
            raise UserError(_(
                'No se encontraron usuarios o contactos asociados a empleados.'
            ))

        date_str = fields.Date.to_string(self.date) if self.date else '-'
        subject = _('Feriado: %s (%s)') % (self.name, date_str)
        body_parts = [
            '<p><b>%s</b></p>' % (self.name or ''),
            '<p><i>%s</i></p>' % date_str,
        ]
        if self.reflective_message:
            body_parts.append(self.reflective_message)
        elif self.description:
            body_parts.append(self.description)
        body = ''.join(body_parts)

        self.message_post(
            body=body, subject=subject,
            partner_ids=partners.ids,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        self.write({
            'notification_sent': True,
            'notification_date': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Aviso enviado'),
                'message': _(
                    'Se notifico a %s persona(s) sobre el feriado "%s".'
                ) % (len(partners), self.name),
                'type': 'success',
                'sticky': False,
            },
        }
