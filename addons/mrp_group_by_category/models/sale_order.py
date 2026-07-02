from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    production_ids = fields.One2many(
        'mrp.production', 'sale_order_id', string='Órdenes de Fabricación')
    production_count = fields.Integer(
        string='Órdenes de Fabricación',
        compute='_compute_production_data')
    workorder_count = fields.Integer(
        string='Operaciones de Fabricación',
        compute='_compute_production_data')
    workorder_completed_qty = fields.Float(
        string='Cantidad Completada',
        compute='_compute_production_data')

    @api.depends('production_ids.workorder_ids.qty_produced')
    def _compute_production_data(self):
        for order in self:
            workorders = order.production_ids.mapped('workorder_ids')
            order.production_count = len(order.production_ids)
            order.workorder_count = len(workorders)
            order.workorder_completed_qty = sum(workorders.mapped('qty_produced'))

    def action_view_productions(self):
        self.ensure_one()
        action = {
            'name': 'Órdenes de Fabricación',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.production_ids.ids)],
            'context': {'create': False}
        }
        if len(self.production_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.production_ids.id
        return action

    def action_configure_manufacturing(self):
        self.ensure_one()
        return {
            'name': 'Configurar Fabricación',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_start_date': fields.Datetime.now(),
            }
        }

    def action_view_manufacturing_factories(self):
        self.ensure_one()
        workorders = self.production_ids.mapped('workorder_ids')
        if not workorders:
            return {'type': 'ir.actions.act_window_close'}

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'name': _('Órdenes de Trabajo'),
            'view_mode': 'list,form',
            'domain': [('id', 'in', workorders.ids)],
            'context': {
                'create': False,
                'edit': False,
            },
            'target': 'current',
        }

        if len(workorders) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = workorders.id

        return action 