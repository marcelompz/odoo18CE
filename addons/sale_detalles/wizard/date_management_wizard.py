from odoo import models, fields, api
from datetime import datetime, timedelta

class DateManagementWizard(models.TransientModel):
    _name = 'date.management.wizard'
    _description = 'Wizard para gestión de fechas de órdenes de venta'

    order_ids = fields.Many2many('sale.order', string='Órdenes de Venta')
    confirmation_date = fields.Date(string='Fecha de Confirmación', default=fields.Date.today)
    validity_date = fields.Date(string='Fecha de Vencimiento')
    set_validity_date = fields.Boolean(string='Establecer Fecha de Vencimiento', default=True)
    days_to_validity = fields.Integer(string='Días hasta Vencimiento', default=30)
    apply_to_all = fields.Boolean(string='Aplicar a Todas las Órdenes', default=True)

    @api.onchange('days_to_validity')
    def _onchange_days_to_validity(self):
        """Calcula automáticamente la fecha de vencimiento basada en los días"""
        if self.confirmation_date and self.days_to_validity:
            self.validity_date = self.confirmation_date + timedelta(days=self.days_to_validity)

    @api.onchange('confirmation_date')
    def _onchange_confirmation_date(self):
        """Recalcula la fecha de vencimiento cuando cambia la fecha de confirmación"""
        if self.confirmation_date and self.days_to_validity:
            self.validity_date = self.confirmation_date + timedelta(days=self.days_to_validity)

    def action_apply_dates(self):
        """Aplica las fechas a las órdenes seleccionadas"""
        for order in self.order_ids:
            vals = {}
            
            # Establecer fecha de confirmación
            if self.confirmation_date:
                vals['confirmation_date'] = self.confirmation_date
            
            # Establecer fecha de vencimiento
            if self.set_validity_date and self.validity_date:
                vals['validity_date'] = self.validity_date
            
            # Aplicar cambios
            if vals:
                order.write(vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fechas Aplicadas',
                'message': f'Se han aplicado las fechas a {len(self.order_ids)} órdenes.',
                'type': 'success',
            }
        }

    def action_validate_dates(self):
        """Valida que las fechas de las órdenes sean coherentes"""
        invalid_orders = []
        for order in self.order_ids:
            if order.confirmation_date and order.validity_date:
                if order.confirmation_date >= order.validity_date:
                    invalid_orders.append(order.name)
        
        if invalid_orders:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Órdenes con Fechas Inválidas',
                    'message': f'Las siguientes órdenes tienen fechas inválidas: {", ".join(invalid_orders)}',
                    'type': 'warning',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Validación Exitosa',
                    'message': 'Todas las órdenes tienen fechas válidas.',
                    'type': 'success',
                }
            } 