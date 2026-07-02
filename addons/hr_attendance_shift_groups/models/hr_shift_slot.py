# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


SLOT_TYPES = [
    ('ordinary', 'Trabajo Ordinario'),
    ('extra_day', 'Extra Diurno'),
    ('extra_night', 'Extra Nocturno'),
    ('break', 'Descanso'),
]


class HrShiftSlot(models.Model):
    _name = 'hr.shift.slot'
    _description = 'Franja Horaria de Turno'
    _order = 'shift_group_id, sequence, time_from'

    shift_group_id = fields.Many2one(
        'hr.shift.group',
        string='Grupo de Turno',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(string='Nombre', required=True, translate=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    time_from = fields.Float(
        string='Hora Inicio',
        required=True,
        help='Hora de inicio en formato decimal (ej. 8.17 = 08:10).',
    )
    time_to = fields.Float(
        string='Hora Fin',
        required=True,
        help='Hora de fin en formato decimal. Para franjas que cruzan la medianoche '
             '(ej. 20:00 a 05:59), use 5.98 como hora de fin.',
    )
    slot_type = fields.Selection(
        SLOT_TYPES,
        string='Tipo',
        required=True,
        default='ordinary',
    )
    crosses_midnight = fields.Boolean(
        string='Cruza Medianoche',
        compute='_compute_crosses_midnight',
        store=True,
    )
    duration = fields.Float(
        string='Duración (h)',
        compute='_compute_duration',
        store=True,
    )
    company_id = fields.Many2one(
        related='shift_group_id.company_id',
        store=True,
    )

    @api.depends('time_from', 'time_to')
    def _compute_crosses_midnight(self):
        for rec in self:
            rec.crosses_midnight = rec.time_to < rec.time_from

    @api.depends('time_from', 'time_to', 'crosses_midnight')
    def _compute_duration(self):
        for rec in self:
            if rec.crosses_midnight:
                rec.duration = (24.0 - rec.time_from) + rec.time_to
            else:
                rec.duration = rec.time_to - rec.time_from

    @api.constrains('time_from', 'time_to')
    def _check_time_range(self):
        for rec in self:
            if not (0.0 <= rec.time_from < 24.0):
                raise ValidationError(
                    _("La hora de inicio de la franja '%s' debe estar entre 0.0 y 23.99.") % rec.name
                )
            if not (0.0 < rec.time_to <= 24.0):
                raise ValidationError(
                    _("La hora de fin de la franja '%s' debe estar entre 0.01 y 24.0.") % rec.name
                )

    def get_segments(self):
        """Devuelve los segmentos [(start, end), ...] de la franja en un día.
        Si cruza medianoche, devuelve dos segmentos."""
        self.ensure_one()
        if self.crosses_midnight:
            return [(self.time_from, 24.0), (0.0, self.time_to)]
        return [(self.time_from, self.time_to)]

    def name_get(self):
        result = []
        for rec in self:
            from_h = int(rec.time_from)
            from_m = int(round((rec.time_from - from_h) * 60))
            to_h = int(rec.time_to)
            to_m = int(round((rec.time_to - to_h) * 60))
            label = "%s (%02d:%02d - %02d:%02d)" % (rec.name, from_h, from_m, to_h, to_m)
            result.append((rec.id, label))
        return result
