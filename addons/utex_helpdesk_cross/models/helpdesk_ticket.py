# -*- coding: utf-8 -*-
"""
Created on 2025-12-04 22:29:20

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTicketInherit(models.Model):
    _inherit = 'helpdesk.ticket'

    def _get_default_allowed_partners(self):
        return self.env.user.helpdesk_allowed_partner_ids

    maintenance_equipment_id = fields.Many2one(
        'maintenance.equipment', string='Equipo afectado', store=True)
    maintenance_type_problem_ids = fields.Many2many(
        'maintenance.type.problem', string='Tipo de problema')
    is_draft_state = fields.Boolean(
        string='Está en borrador/nuevo?', compute='_compute_is_draft_state')
    name = fields.Char(
        string='Referencia', compute='_compute_name', store=True, readonly=False, required=True, index=True, tracking=True)
    team_equipment_ids = fields.Many2many(
        related='team_id.equipment_ids', string='Máquinas del Equipo (Auxiliar)')
    current_user_allowed_partners = fields.Many2many(
        'res.partner', compute='_compute_current_user_allowed_partners', default=_get_default_allowed_partners, store=False)

    @api.depends_context('uid')
    def _compute_current_user_allowed_partners(self):
        user = self.env.user
        for record in self:
            if user.helpdesk_allowed_partner_ids:
                record.current_user_allowed_partners = user.helpdesk_allowed_partner_ids
            
            else:
                record.current_user_allowed_partners = False

    @api.depends('maintenance_type_problem_ids')
    def _compute_name(self):
        for record in self:
            names = record.maintenance_type_problem_ids.mapped('name')
            
            if names:
                record.name = " - ".join(names)

            else:
                record.name = False

    @api.depends('stage_id.sequence')
    def _compute_is_draft_state(self):
        first_stage = self.env['helpdesk.stage'].search([], order='sequence asc', limit=1)
        min_sequence = first_stage.sequence if first_stage else 0

        for record in self:
            if not record.stage_id:
                record.is_draft_state = True

            else:
                record.is_draft_state = record.stage_id.sequence == min_sequence
    
    @api.onchange('team_id')
    def _onchange_team_id(self):
        self.user_id = self.team_id.property_res_users_id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self.partner_id = self.user_id.partner_id

    def action_save_and_return(self):
        action = self.env['ir.actions.act_window']._for_xml_id('helpdesk.helpdesk_ticket_action_main_my')
        
        return action
    