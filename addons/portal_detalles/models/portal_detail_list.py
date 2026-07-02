# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PortalDetailList(models.Model):
    _name = 'portal.detail.list'
    _description = 'Lista Portal del Cliente'
    _order = 'create_date desc'

    name = fields.Char('Número de Lista', required=True, default='Nuevo')
    config_id = fields.Many2one('portal.detail.config', 'Configuración', required=True, ondelete='cascade')
    order_id = fields.Many2one('sale.order', 'Pedido', related='config_id.order_id', store=True)
    customer_id = fields.Many2one('res.partner', 'Cliente', related='config_id.customer_id', store=True)
    commercial_id = fields.Many2one('res.users', 'Comercial', related='config_id.commercial_id', store=True)

    # Estado de la lista
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviada'),
        ('reviewed', 'Revisada'),
        ('processed', 'Procesada'),
        ('rejected', 'Rechazada')
    ], default='draft', tracking=True)

    # Fechas
    submitted_date = fields.Datetime('Fecha de Envío')
    reviewed_date = fields.Datetime('Fecha de Revisión')
    create_date = fields.Datetime('Fecha de Creación', readonly=True)
    write_date = fields.Datetime('Última Modificación', readonly=True)

    # Notificaciones
    commercial_notified = fields.Boolean('Comercial Notificado', default=False)
    notification_date = fields.Datetime('Fecha Notificación')
    customer_notified = fields.Boolean('Cliente Notificado', default=False)

    # Items de la lista
    detail_items = fields.One2many('portal.detail.item', 'list_id', 'Items de la Lista')
    item_count = fields.Integer('Cantidad de Items', compute='_compute_item_count')

    # Observaciones
    customer_notes = fields.Text('Observaciones del Cliente')
    commercial_notes = fields.Text('Observaciones del Comercial')

    # Estadísticas
    total_items = fields.Integer('Total Items', compute='_compute_statistics')
    approved_items = fields.Integer('Items Aprobados', compute='_compute_statistics')
    rejected_items = fields.Integer('Items Rechazados', compute='_compute_statistics')
    pending_items = fields.Integer('Items Pendientes', compute='_compute_statistics')

    @api.depends('detail_items')
    def _compute_item_count(self):
        for record in self:
            record.item_count = len(record.detail_items)

    @api.depends('detail_items.state')
    def _compute_statistics(self):
        for record in self:
            items = record.detail_items
            record.total_items = len(items)
            record.approved_items = len(items.filtered(lambda x: x.state == 'approved'))
            record.rejected_items = len(items.filtered(lambda x: x.state == 'rejected'))
            record.pending_items = len(items.filtered(lambda x: x.state == 'pending'))

    @api.model
    def create(self, vals):
        """Sobrescribir creación para generar nombre automático"""
        if not vals.get('name') or vals.get('name') == 'Nuevo':
            config = self.env['portal.detail.config'].browse(vals.get('config_id'))
            if config and config.order_id:
                timestamp = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
                vals['name'] = f"LIST-{config.order_id.name}-{timestamp}"
        return super().create(vals)

    def action_submit(self):
        """Enviar lista"""
        for record in self:
            record.state = 'submitted'
            record.submitted_date = fields.Datetime.now()
            record._send_notification_to_commercial()

    def action_review(self):
        """Marcar como revisada"""
        for record in self:
            record.state = 'reviewed'
            record.reviewed_date = fields.Datetime.now()

    def action_process(self):
        """Procesar lista"""
        for record in self:
            record.state = 'processed'
            record._send_notification_to_customer()

    def action_reject(self):
        """Rechazar lista"""
        for record in self:
            record.state = 'rejected'
            record._send_notification_to_customer()

    def action_reset_to_draft(self):
        """Volver a borrador"""
        for record in self:
            record.state = 'draft'
            record.submitted_date = False
            record.reviewed_date = False

    def _send_notification_to_commercial(self):
        """Enviar notificación al comercial"""
        for record in self:
            if not record.commercial_notified:
                template = self.env.ref('portal_detalles.email_template_list_submitted')
                template.send_mail(record.id, force_send=True)
                record.commercial_notified = True
                record.notification_date = fields.Datetime.now()

    def _send_notification_to_customer(self):
        """Enviar notificación al cliente"""
        for record in self:
            if not record.customer_notified:
                if record.state == 'processed':
                    template = self.env.ref('portal_detalles.email_template_list_processed')
                elif record.state == 'rejected':
                    template = self.env.ref('portal_detalles.email_template_list_rejected')
                else:
                    return
                
                template.send_mail(record.id, force_send=True)
                record.customer_notified = True

    def action_approve_all_items(self):
        """Aprobar todos los items"""
        for record in self:
            record.detail_items.write({'state': 'approved'})

    def action_reject_all_items(self):
        """Rechazar todos los items"""
        for record in self:
            record.detail_items.write({'state': 'rejected'})

    def action_reset_all_items(self):
        """Resetear todos los items a pendiente"""
        for record in self:
            record.detail_items.write({'state': 'pending'})

    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name}"
            if record.order_id:
                name += f" - {record.order_id.name}"
            if record.customer_id:
                name += f" ({record.customer_id.name})"
            result.append((record.id, name))
        return result

    def copy(self, default=None):
        """Sobrescribir copia para resetear estado"""
        default = default or {}
        default.update({
            'state': 'draft',
            'submitted_date': False,
            'reviewed_date': False,
            'commercial_notified': False,
            'customer_notified': False,
            'notification_date': False,
        })
        return super().copy(default)

    @api.constrains('detail_items')
    def _check_items_required(self):
        """Validar que tenga al menos un item"""
        for record in self:
            if record.state == 'submitted' and not record.detail_items:
                raise ValidationError(_('La lista debe tener al menos un item para poder ser enviada.'))

    def action_view_items(self):
        """Ver items de la lista"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Items de la Lista'),
            'res_model': 'portal.detail.item',
            'view_mode': 'list,form',
            'domain': [('list_id', '=', self.id)],
            'context': {'default_list_id': self.id},
        }

    def action_export_excel(self):
        """Descargar exportación XLSX de los items de la lista."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/portal_detalles/export_xlsx/{self.id}',
            'target': 'self',
        }
