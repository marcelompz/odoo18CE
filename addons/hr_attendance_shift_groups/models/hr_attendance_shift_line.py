# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrAttendanceShiftLine(models.Model):
    _name = 'hr.attendance.shift.line'
    _description = 'Linea de Distribucion de Horas por Franja'
    _order = 'date, attendance_id, slot_sequence'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Asistencia',
        required=True,
        ondelete='cascade',
        index=True,
    )
    slot_id = fields.Many2one(
        'hr.shift.slot',
        string='Franja Horaria',
        required=True,
        ondelete='restrict',
    )
    slot_sequence = fields.Integer(
        related='slot_id.sequence',
        store=True,
        string='Secuencia',
    )
    slot_type = fields.Selection(
        related='slot_id.slot_type',
        store=True,
        string='Tipo',
    )
    employee_id = fields.Many2one(
        related='attendance_id.employee_id',
        store=True,
        index=True,
    )
    shift_group_id = fields.Many2one(
        related='attendance_id.shift_group_id',
        store=True,
        string='Grupo de Turno',
    )
    # FECHA REAL CALENDARIO de esta porcion de horas (no necesariamente igual al
    # shift_date de la asistencia: una asistencia que cruza medianoche genera
    # lineas con fechas DIFERENTES).
    date = fields.Date(
        string='Fecha (calendario)',
        required=True,
        index=True,
        help='Fecha calendario real a la que pertenecen estas horas. '
             'Diferente del shift_date de la asistencia cuando cruza medianoche.',
    )
    hours_worked = fields.Float(
        string='Horas',
        digits=(5, 4),
        required=True,
        default=0.0,
    )
    company_id = fields.Many2one(
        related='attendance_id.employee_id.company_id',
        store=True,
    )

    # ------------------------------------------------------------------
    # Crossnexion: limpieza segura para admin
    # ------------------------------------------------------------------
    @api.model
    def action_clear_all_admin(self):
        """Borra TODAS las filas de hr.attendance.shift.line.
        Util cuando se quiere recalcular desde cero. Solo admin."""
        from odoo.exceptions import UserError
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('Solo administradores pueden ejecutar esta operacion.'))
        count = self.env['hr.attendance.shift.line'].sudo().search_count([])
        self.env.cr.execute('DELETE FROM hr_attendance_shift_line')
        self.invalidate_model()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lineas eliminadas'),
                'message': _(
                    'Se eliminaron %d lineas de turno. Use "Recalcular Periodo" '
                    'para regenerarlas.'
                ) % count,
                'type': 'success',
                'sticky': True,
            },
        }
