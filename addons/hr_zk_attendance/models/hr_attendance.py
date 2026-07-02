# -*- coding: utf-8 -*-
################################################################################
#
#    Crossnexion - UTEX RRHH
#
################################################################################
from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime


class HrAttendance(models.Model):
    """Crossnexion: UTEX importa marcaciones historicas del reloj ZK.

    Por diseno, un dia con un solo fichaje queda como marcacion ABIERTA
    (``check_out`` vacio) para que ``hr_attendance_shift_groups`` la marque como
    ``is_incomplete`` (reason ``no_checkout``) y aparezca en
    "Correccion de Marcaciones".

    El core de Odoo (``_check_validity``) solo permite UNA marcacion abierta por
    empleado; esto rompe la descarga masiva cuando un empleado tiene varios dias
    con un solo fichaje (se crean varias abiertas en la misma transaccion y toda
    la descarga se revierte). Reemplazamos la validacion: se sigue impidiendo el
    SOLAPAMIENTO entre marcaciones, pero se PERMITEN multiples marcaciones
    abiertas por empleado.
    """
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        for attendance in self:
            # Marcacion anterior mas reciente con check_in <= al nuestro.
            last_before_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            # Solapamiento: la anterior estaba cerrada y su salida cae despues
            # de nuestra entrada.
            if (last_before_in and last_before_in.check_out
                    and last_before_in.check_out > attendance.check_in):
                raise ValidationError(_(
                    "Cannot create new attendance record for %(empl_name)s, "
                    "the employee was already checked in on %(datetime)s",
                    empl_name=attendance.employee_id.name,
                    datetime=format_datetime(
                        self.env, attendance.check_in, dt_format=False)))

            # Crossnexion: se OMITE a proposito el limite core de "una sola
            # marcacion abierta por empleado". Multiples abiertas son validas
            # (dias historicos con un solo fichaje pendientes de correccion).
            if attendance.check_out:
                last_before_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_before_out and last_before_in != last_before_out:
                    raise ValidationError(_(
                        "Cannot create new attendance record for %(empl_name)s, "
                        "the employee was already checked in on %(datetime)s",
                        empl_name=attendance.employee_id.name,
                        datetime=format_datetime(
                            self.env, last_before_out.check_in,
                            dt_format=False)))
