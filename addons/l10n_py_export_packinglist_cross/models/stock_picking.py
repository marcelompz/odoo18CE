# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_export = fields.Boolean(
        string='Es Exportacion', copy=False,
        help='Marcar si esta remision corresponde a una operacion de exportacion. '
             'Habilita la generacion del Packing List.',
    )
    packing_list_ids = fields.One2many(
        comodel_name='stock.packing.list', inverse_name='picking_id',
        string='Packing Lists',
    )
    packing_list_count = fields.Integer(
        string='Cantidad de Packing Lists',
        compute='_compute_packing_list_count',
        store=True,
    )
    show_packing_list_button = fields.Boolean(
        string='Mostrar Boton Packing List',
        compute='_compute_show_packing_list_button',
        store=True,
    )

    @api.depends('packing_list_ids')
    def _compute_packing_list_count(self):
        for rec in self:
            rec.packing_list_count = len(rec.packing_list_ids)

    @api.depends('is_export', 'partner_id', 'partner_id.country_id',
                 'company_id', 'company_id.country_id', 'picking_type_id', 'picking_type_id.code')
    def _compute_show_packing_list_button(self):
        for rec in self:
            show = False
            if rec.picking_type_id and rec.picking_type_id.code == 'outgoing':
                if rec.is_export:
                    show = True
                elif (rec.partner_id and rec.partner_id.country_id and
                      rec.company_id and rec.company_id.country_id and
                      rec.partner_id.country_id != rec.company_id.country_id):
                    show = True
            rec.show_packing_list_button = show

    def action_open_packing_list_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generar Packing List'),
            'res_model': 'stock.packing.list.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'active_model': 'stock.picking',
                'active_id': self.id,
            },
        }

    def action_view_packing_lists(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Packing Lists'),
            'res_model': 'stock.packing.list',
            'context': {
                'default_picking_id': self.id,
                'default_consignee_partner_id': self.partner_id.id,
            },
        }
        if self.packing_list_count == 1:
            action.update({'view_mode': 'form', 'res_id': self.packing_list_ids.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('picking_id', '=', self.id)]})
        return action
