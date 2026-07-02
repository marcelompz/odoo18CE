# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    shift_group_id = fields.Many2one(
        'hr.shift.group',
        string='Grupo de Turno',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help='Grupo de turno aplicable durante la vigencia del contrato. '
             'Tiene prioridad sobre el grupo asignado al empleado.',
    )

    @api.onchange('shift_group_id')
    def _onchange_shift_group_id(self):
        """Al asignar un grupo de turno al contrato, autoasignar uno de los
        Horarios de Trabajo (resource.calendar) vinculados al grupo si el
        actual no esta entre ellos."""
        if not self.shift_group_id:
            return
        candidates = self.shift_group_id.resource_calendar_ids
        if not candidates:
            return
        if self.resource_calendar_id and self.resource_calendar_id in candidates:
            return
        comp_match = candidates.filtered(lambda c: c.company_id == self.company_id)
        self.resource_calendar_id = (comp_match[:1] or candidates[:1]).id
