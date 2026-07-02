# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrShiftGroup(models.Model):
    _name = 'hr.shift.group'
    _description = 'Grupo de Turno'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True,
        help='Nombre del grupo de turno (ej. Operativo, Administrativo).')
    code = fields.Char(string='Codigo', help='Codigo corto del grupo (opcional).')
    description = fields.Text(string='Descripcion', translate=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Empresa',
        default=lambda self: self.env.company, required=True)
    slot_ids = fields.One2many('hr.shift.slot', 'shift_group_id',
        string='Franjas Horarias', copy=True)
    employee_ids = fields.One2many('hr.employee', 'shift_group_id',
        string='Empleados Asignados')
    employee_count = fields.Integer(string='# Empleados',
        compute='_compute_employee_count')
    color = fields.Integer(string='Color', default=0)

    # Vinculo con Horario de Trabajo (resource.calendar) — opcional
    resource_calendar_ids = fields.Many2many(
        'resource.calendar',
        'hr_shift_group_resource_calendar_rel',
        'shift_group_id', 'calendar_id',
        string='Horarios de Trabajo Vinculados',
        help='Horarios de trabajo (resource.calendar) vinculados a este grupo de turno. '
             'Si un empleado tiene uno de estos horarios en su contrato/empleado, el sistema '
             'asignara automaticamente este grupo de turno a sus asistencias.',
    )

    # Tolerancias de marcacion
    tolerance_morning_minutes = fields.Integer(
        string='Tolerancia entrada (min)', default=15,
        help='Minutos de tolerancia al inicio de la jornada. Si el empleado marca check-in '
             'dentro de este margen alrededor del inicio oficial del turno, se considera '
             'puntual (no genera hora extra ni descuento).',
    )
    tolerance_evening_minutes = fields.Integer(
        string='Tolerancia salida (min)', default=25,
        help='Minutos de tolerancia al fin de la jornada. Si el empleado marca check-out '
             'dentro de este margen alrededor del fin oficial del turno, se considera '
             'salida normal (no genera hora extra ni descuento).',
    )
    hard_limit_minutes = fields.Integer(
        string='Limite extra/descuento (min) [legacy]', default=30,
        help='LEGACY. Reemplazado por los limites separados de ENTRADA y SALIDA. '
             'Se mantiene como respaldo: si el limite de entrada o de salida es 0, '
             'se usa este valor.',
    )
    hard_limit_entry_minutes = fields.Integer(
        string='Limite extra/descuento ENTRADA (min)', default=30,
        help='Limite duro de la tolerancia de ENTRADA. Si la tardanza respecto del '
             'inicio oficial SUPERA estos minutos, se PIERDE la tolerancia y se '
             'descuenta TODO desde el inicio oficial. Dentro del limite rige la '
             'tolerancia (zona franca). 0 = usar el limite legacy.',
    )
    hard_limit_exit_minutes = fields.Integer(
        string='Limite extra/descuento SALIDA (min)', default=30,
        help='Limite duro de la tolerancia de SALIDA. Si la diferencia respecto del '
             'fin oficial SUPERA estos minutos, se PIERDE la tolerancia y se cuenta '
             'TODO desde el fin oficial (extra si salio despues, descuento si salio '
             'temprano). Dentro del limite rige la tolerancia (zona franca). '
             '0 = usar el limite legacy.',
    )

    def get_hard_limits_minutes(self):
        """Devuelve (limite_entrada, limite_salida) en MINUTOS, con fallback al
        campo legacy si alguno esta en 0."""
        self.ensure_one()
        legacy = self.hard_limit_minutes or 30
        entry = self.hard_limit_entry_minutes or legacy
        exit_ = self.hard_limit_exit_minutes or legacy
        return entry, exit_

    def get_shift_official_bounds(self):
        """Devuelve (inicio_oficial, fin_oficial) en horas decimales del dia.
        Inicio: time_from de la primera franja ORDINARIA que no cruza medianoche.
        Fin: time_to de la ultima franja ORDINARIA que no cruza medianoche.
        Devuelve (None, None) si no hay franjas ordinarias."""
        self.ensure_one()
        ords = self.slot_ids.filtered(
            lambda s: s.slot_type == 'ordinary' and not s.crosses_midnight
        )
        if not ords:
            return None, None
        ords_sorted = ords.sorted('time_from')
        return ords_sorted[0].time_from, ords_sorted[-1].time_to

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = len(rec.employee_ids)

    @api.constrains('slot_ids')
    def _check_slots(self):
        """Validar slots: al menos uno y sin solapamientos."""
        for group in self:
            if not group.slot_ids:
                raise ValidationError(
                    _("El grupo de turno '%s' debe tener al menos una franja horaria.") % group.name
                )
            segments = []
            for slot in group.slot_ids:
                if slot.time_from == slot.time_to:
                    raise ValidationError(
                        _("La franja '%s' tiene la misma hora de inicio y fin.") % slot.name
                    )
                if slot.crosses_midnight:
                    segments.append((slot, slot.time_from, 24.0))
                    segments.append((slot, 0.0, slot.time_to))
                else:
                    segments.append((slot, slot.time_from, slot.time_to))
            segments_sorted = sorted(segments, key=lambda x: x[1])
            for i in range(len(segments_sorted) - 1):
                _slot_a, _, end_a = segments_sorted[i]
                slot_b, start_b, _ = segments_sorted[i + 1]
                if start_b < end_a - 1e-6:
                    raise ValidationError(
                        _("Las franjas '%s' y '%s' se solapan en el grupo '%s'.")
                        % (segments_sorted[i][0].name, slot_b.name, group.name)
                    )

    def get_ordered_slots(self):
        """Franjas ordenadas para presentacion (cruzadas de medianoche al final)."""
        self.ensure_one()
        normal = self.slot_ids.filtered(lambda s: not s.crosses_midnight).sorted('time_from')
        crossed = self.slot_ids.filtered(lambda s: s.crosses_midnight).sorted('time_from')
        return normal + crossed

    def get_visible_slots(self):
        """Franjas visibles en tablero (excluye descansos)."""
        return self.get_ordered_slots().filtered(lambda s: s.slot_type != 'break')

    @api.model
    def find_by_calendar(self, calendar):
        """Devuelve el grupo de turno asociado a un resource.calendar dado.
        Util para auto-deducir el grupo desde el horario de trabajo del empleado."""
        if not calendar:
            return self.browse()
        return self.search([
            ('resource_calendar_ids', 'in', calendar.ids),
            ('active', '=', True),
        ], limit=1)
