# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Nuevo: campos generales de licencia (cubren remunerada y no remunerada)
    leave_id = fields.Many2one(
        'hr.leave',
        string='Licencia asociada',
        index=True,
        ondelete='set null',
        help='Solicitud de tiempo personal que origino esta entrada.',
    )
    is_leave_attendance = fields.Boolean(
        string='Asistencia por Licencia',
        default=False,
        index=True,
        help='Si esta marcado, esta entrada fue generada automaticamente '
             'por una licencia aprobada (vacaciones, enfermedad, etc.).',
    )
    leave_is_remunerated = fields.Boolean(
        string='Licencia Remunerada',
        default=False,
        index=True,
        help='True si la licencia que origino esta entrada es remunerada.',
    )
    leave_type_name = fields.Char(
        string='Tipo de Licencia',
        help='Nombre del tipo de tiempo personal (Vacaciones, Reposo, etc.).',
    )

    # Backward compat (mantener los campos anteriores como espejo)
    unremunerated_absence = fields.Boolean(
        string='Falta sin remuneracion',
        default=False,
        index=True,
    )
    unremunerated_leave_id = fields.Many2one(
        'hr.leave',
        string='Solicitud asociada (no rem.)',
        index=True,
        ondelete='set null',
    )

    def write(self, vals):
        # Bloquear edicion si esta marcado como inasistencia no remunerada,
        # excepto los propios campos de licencia.
        allowed_keys = {
            'leave_id', 'is_leave_attendance',
            'leave_is_remunerated', 'leave_type_name',
            'unremunerated_absence', 'unremunerated_leave_id',
        }
        if any(rec.is_leave_attendance for rec in self):
            if not set(vals.keys()).issubset(allowed_keys):
                if not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                    raise UserError(_(
                        'Esta asistencia esta vinculada a una licencia '
                        'aprobada y no puede modificarse. Para editarla, '
                        'rechace la licencia asociada o contacte a un '
                        'responsable de Tiempo Personal.'
                    ))
        return super().write(vals)
