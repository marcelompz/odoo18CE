# -*- coding: utf-8 -*-

import secrets
import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PortalDetailConfig(models.Model):
    _name = 'portal.detail.config'
    _description = 'Configuración de Listas Portal'
    _order = 'create_date desc'

    name = fields.Char('Nombre de la Configuración', required=True)
    order_id = fields.Many2one('sale.order', 'Pedido', required=True)
    customer_id = fields.Many2one('res.partner', 'Cliente', related='order_id.partner_id', store=True)
    commercial_id = fields.Many2one('res.users', 'Comercial Responsable', required=True, default=lambda self: self.env.user)

    # Configuración de acceso
    is_active = fields.Boolean('Activo', default=True)
    expires_date = fields.Datetime('Fecha de Expiración')

    # Configuración de productos
    available_categories = fields.Many2many('product.category', string='Categorías Disponibles')
    available_sizes = fields.Many2many('product.attribute.value', string='Talles Disponibles',
                                      domain=[('attribute_id.name', 'ilike', 'talle')])

    # URLs generadas
    portal_url = fields.Char('URL del Portal', compute='_compute_portal_url', store=True)

    # Estado y seguimiento
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('expired', 'Expirado'),
        ('cancelled', 'Cancelado')
    ], default='draft', tracking=True)

    # Relaciones
    detail_lists = fields.One2many('portal.detail.list', 'config_id', 'Listas Enviadas')
    list_count = fields.Integer('Cantidad de Listas', compute='_compute_list_count')

    # Fechas
    create_date = fields.Datetime('Fecha de Creación', readonly=True)
    write_date = fields.Datetime('Última Modificación', readonly=True)

    @api.depends('detail_lists')
    def _compute_list_count(self):
        for record in self:
            record.list_count = len(record.detail_lists)

    @api.depends('order_id')
    def _compute_portal_url(self):
        for record in self:
            if record.order_id:
                # Asegurar que el pedido tenga token de portal
                record.order_id._portal_ensure_token()
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.portal_url = f"{base_url}/portal/upload-details?order_id={record.order_id.id}&token={record.order_id.access_token}"
            else:
                record.portal_url = False


    def action_activate(self):
        """Activar configuración"""
        for record in self:
            record.state = 'active'
            record.is_active = True

    def action_expire(self):
        """Expirar configuración"""
        for record in self:
            record.state = 'expired'
            record.is_active = False

    def action_cancel(self):
        """Cancelar configuración"""
        for record in self:
            record.state = 'cancelled'
            record.is_active = False

    def action_regenerate_token(self):
        """Regenerar token de acceso del pedido"""
        for record in self:
            if record.order_id:
                # Regenerar token del pedido
                record.order_id.access_token = False
                record.order_id._portal_ensure_token()
                record.portal_url = False  # Forzar recálculo

    @api.constrains('expires_date')
    def _check_expires_date(self):
        """Validar fecha de expiración"""
        for record in self:
            if record.expires_date and record.expires_date < fields.Datetime.now():
                raise ValidationError(_('La fecha de expiración no puede ser anterior a la fecha actual.'))

    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name} - {record.order_id.name}"
            if record.customer_id:
                name += f" ({record.customer_id.name})"
            result.append((record.id, name))
        return result

    def copy(self, default=None):
        """Sobrescribir copia para resetear estado"""
        default = default or {}
        default['state'] = 'draft'
        return super().copy(default)

    def action_view_lists(self):
        """Ver listas enviadas"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Listas Enviadas'),
            'res_model': 'portal.detail.list',
            'view_mode': 'list,form',
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }

    def action_send_link_to_customer(self):
        """Enviar enlace al cliente por email"""
        self.ensure_one()
        template = self.env.ref('portal_detalles.email_template_config_link')
        template.send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Enlace Enviado'),
                'message': _('El enlace ha sido enviado al cliente por email.'),
                'type': 'success',
            }
        }
