# -*- coding: utf-8 -*-
################################################################################
#
#    Crossnexion - Mapeo de IDs del reloj biometrico a empleados.
#
#    Un mismo empleado puede estar enrolado en el reloj bajo VARIOS user_id
#    (re-enrolamiento, doble huella/cara, cambio de equipo). Este modelo
#    permite que un empleado tenga muchos IDs de reloj sin duplicarse.
#
################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrZkDeviceUser(models.Model):
    """Relacion ID del reloj (user_id) -> empleado de Odoo."""
    _name = 'hr.zk.device.user'
    _description = 'ID de Reloj Biometrico del Empleado'
    _rec_name = 'device_uid'

    device_uid = fields.Char(
        string='ID en el Reloj', required=True, index=True,
        help='user_id tal como lo entrega el dispositivo biometrico.')
    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True,
        ondelete='cascade', index=True)
    device_name = fields.Char(
        string='Nombre en el Reloj',
        help='Nombre con el que figura la persona en el dispositivo.')

    _sql_constraints = [
        ('device_uid_uniq', 'unique(device_uid)',
         'Ese ID de reloj ya esta asignado a otro empleado.'),
    ]

    @api.model
    def _normalize_uid(self, device_uid):
        return str(device_uid or '').strip()

    @api.model
    def _employee_for_uid(self, device_uid):
        """Devuelve el empleado mapeado a ese ID de reloj, o recordset vacio."""
        rec = self.search(
            [('device_uid', '=', self._normalize_uid(device_uid))], limit=1)
        return rec.employee_id

    @api.model
    def _register_uid(self, device_uid, employee, device_name=False):
        """Registra (si no existe) el ID del reloj para el empleado.
        Si ya existe el mapeo, NO lo reasigna (la tabla manda)."""
        device_uid = self._normalize_uid(device_uid)
        if not device_uid or not employee:
            return self.browse()
        rec = self.search([('device_uid', '=', device_uid)], limit=1)
        if rec:
            if device_name and rec.device_name != device_name:
                rec.device_name = device_name
            return rec
        return self.create({
            'device_uid': device_uid,
            'employee_id': employee.id,
            'device_name': device_name or False,
        })
