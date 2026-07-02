# -*- coding: utf-8 -*-
"""
Created on 2025-11-28 11:12:03

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    production_wave_id = fields.Many2one(
        'production.wave', string="Ola de Producción", readonly=True, copy=False)

    def action_create_production_wave(self):
        # 1. Validaciones
        # Filtramos las que no están confirmadas
        not_valid_orders = self.filtered(lambda so: so.state in ['draft', 'cancel'])
        
        if not_valid_orders:
            raise UserError(_("Solo puedes crear una Ola de Producción con cotizaciones confirmadas."))

        # Filtramos solo las que están confirmadas
        valid_orders = self.filtered(lambda so: so.state in ['sale', 'sent'])
        # Verificamos si alguna ya pertenece a una ola
        orders_with_wave = valid_orders.filtered(lambda so: so.production_wave_id)
        if orders_with_wave:
            names = ", ".join(orders_with_wave.mapped('name'))
            raise UserError(_("Las siguientes órdenes ya pertenecen a una Ola de Producción: %s") % names)

        # 2. Crear la Ola de Producción        
        wave = self.env['production.wave'].create({
            'sale_order_ids': [Command.set(valid_orders.ids)],
        })

        # wave.action_calculate_requirements()

        # 3. Redirigir al usuario a la vista formulario de la nueva Ola
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ola de Producción Creada'),
            'res_model': 'production.wave',
            'res_id': wave.id,
            'view_mode': 'form',
            'target': 'current',
        }
