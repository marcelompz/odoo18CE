# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Bhagyadev KP (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ZkMachineAttendance(models.Model):
    """Model to hold data from the biometric device"""
    _name = 'zk.machine.attendance'
    _description = 'Attendance'
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """Overriding the __check_validity function for employee attendance."""
        pass

    device_id_num = fields.Char(
        string='Biometric Device ID',
        help='The ID of the Biometric Device',
    )
    punch_type = fields.Selection(
        [('0', 'Check In'), ('1', 'Check Out'),
         ('2', 'Break Out'), ('3', 'Break In'),
         ('4', 'Overtime In'), ('5', 'Overtime Out'),
         ('255', 'Duplicate')],
        string='Punching Type',
        help='Punching type of the attendance',
    )
    attendance_type = fields.Selection(
        [('1', 'Finger'), ('15', 'Face'),
         ('2', 'Type_2'), ('3', 'Password'),
         ('4', 'Card'), ('255', 'Duplicate')],
        string='Category',
        help='Attendance detecting methods',
    )
    punching_time = fields.Datetime(
        string='Punching Time',
        help='Punching time in the device',
    )
    address_id = fields.Many2one(
        'res.partner',
        string='Working Address',
        help='Working address of the employee',
    )

    # ------------------------------------------------------------------
    # Crossnexion: limpieza segura de marcaciones capturadas (solo admin)
    # ------------------------------------------------------------------
    @api.model
    def action_clear_all_captured(self):
        """Borra TODAS las marcaciones capturadas en la base de datos
        (zk_machine_attendance). NO toca el reloj fisico.
        Util para volver a descargar marcaciones desde cero.
        Solo permitido para administradores (base.group_system).
        """
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_(
                'Solo los administradores del sistema pueden ejecutar esta '
                'operacion.'
            ))
        count = self.env['zk.machine.attendance'].sudo().search_count([])
        self.env.cr.execute('DELETE FROM zk_machine_attendance')
        self.invalidate_model()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marcaciones eliminadas'),
                'message': _(
                    'Se eliminaron %d marcaciones de la base de datos. '
                    'El reloj NO fue afectado. Use "Download Data" para '
                    'volver a descargar las marcaciones.'
                ) % count,
                'type': 'success',
                'sticky': True,
            },
        }
