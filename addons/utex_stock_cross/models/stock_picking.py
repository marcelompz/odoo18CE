# -*- coding: utf-8 -*-
"""
Created on 2025-08-19 10:00:29

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    partner_delivery_address = fields.Char(
        string='Dirección de Entrega', compute='_compute_partner_delivery_address', store=True)
    commercial_user_id = fields.Many2one(
        related='sale_id.user_id', string='Comercial')

    @api.depends('partner_id', 'partner_id.street', 'partner_id.street2', 'partner_id.city',
                 'partner_id.state_id', 'partner_id.country_id')
    def _compute_partner_delivery_address(self):
        for picking in self:
            if picking.partner_id:
                address_parts = [
                    picking.partner_id.street or '',
                    picking.partner_id.street2 or '',
                    picking.partner_id.city or '',
                    picking.partner_id.state_id.name or '',
                    picking.partner_id.country_id.name or ''
                ]
                # Filter out empty parts and join with commas
                picking.partner_delivery_address = ', '.join(filter(None, address_parts))
            else:
                picking.partner_delivery_address = ''

    def action_view_current_picking(self):
        """
        Acción para abrir el traslado actual en una vista de formulario modal.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ver Traslado',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('stock.view_picking_form').id, 'form')],
            'target': 'new',
        }

    @api.constrains('scheduled_date', 'end_transfer_date')
    def _check_transfer_dates_consistency(self):
        """
        Valida que la fecha programada no sea posterior a la fecha fin de traslado.
        """
        for picking in self:
            # Solo validamos si ambos campos tienen valor para evitar errores con False
            if picking.scheduled_date and picking.end_transfer_date and picking.fiscal_document:
                
                # Comparación directa de Datetimes
                if picking.scheduled_date > picking.end_transfer_date:
                    raise ValidationError(_(
                        "Error de Fechas:\n"
                        "La 'Fecha Programada' (%s) no puede ser mayor "
                        "a la 'Fecha Fin de Traslado' (%s)."
                    ) % (picking.scheduled_date, picking.end_transfer_date))
