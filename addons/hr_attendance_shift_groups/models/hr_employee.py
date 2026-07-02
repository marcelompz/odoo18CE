# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    shift_group_id = fields.Many2one(
        'hr.shift.group',
        string='Grupo de Turno',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help='Grupo de turno asignado al empleado. '
             'Si el contrato vigente tiene un grupo, prevalece sobre este.',
    )

    @api.onchange('shift_group_id')
    def _onchange_shift_group_id(self):
        """Al asignar un grupo de turno, sugerir automaticamente uno de los
        Horarios de Trabajo (resource.calendar) vinculados al grupo.
        - Si el grupo tiene calendars vinculados y el actual NO esta entre ellos,
          asignar el primero.
        - Si el grupo tiene 0 calendars vinculados, no hacer nada.
        """
        if not self.shift_group_id:
            return
        candidates = self.shift_group_id.resource_calendar_ids
        if not candidates:
            return
        if self.resource_calendar_id and self.resource_calendar_id in candidates:
            return  # ya esta alineado
        # Tomar el primero que coincida con la empresa, o el primero de todos
        comp_match = candidates.filtered(lambda c: c.company_id == self.company_id)
        self.resource_calendar_id = (comp_match[:1] or candidates[:1]).id

    def get_active_shift_group(self, date=None):
        """Devuelve el grupo de turno efectivo del empleado en una fecha dada.

        Prioridad:
        1. shift_group_id del contrato vigente (asignacion explicita)
        2. shift_group_id del empleado (asignacion explicita)
        3. Grupo cuyo resource_calendar_ids incluye el calendar del contrato/empleado
        """
        self.ensure_one()
        ShiftGroup = self.env['hr.shift.group']

        contract = self._get_contract_at(date) if hasattr(self, '_get_contract_at') else False
        if not contract:
            contract = self.contract_id if 'contract_id' in self._fields else False
            if contract and date and contract.date_start and contract.date_start > date:
                contract = False
            if contract and date and contract.date_end and contract.date_end < date:
                contract = False

        if contract and contract.shift_group_id:
            return contract.shift_group_id
        if self.shift_group_id:
            return self.shift_group_id
        calendar = False
        if contract and contract.resource_calendar_id:
            calendar = contract.resource_calendar_id
        elif self.resource_calendar_id:
            calendar = self.resource_calendar_id
        if calendar:
            grp = ShiftGroup.find_by_calendar(calendar)
            if grp:
                return grp
        return ShiftGroup.browse()

    def _get_contract_at(self, date):
        self.ensure_one()
        if 'hr.contract' not in self.env:
            return False
        domain = [('employee_id', '=', self.id), ('state', 'in', ('open', 'close'))]
        if date:
            domain += ['|', ('date_end', '=', False), ('date_end', '>=', date)]
            domain += [('date_start', '<=', date)]
        return self.env['hr.contract'].search(domain, order='date_start desc', limit=1)
