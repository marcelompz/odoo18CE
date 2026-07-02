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
import datetime
import logging
import re
import unicodedata
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


def _normalize_name(name):
    """Normaliza un nombre para comparar: sin acentos, MAYUSCULAS, sin
    puntuacion y con espacios colapsados. Sirve para emparejar el nombre del
    reloj con el del empleado evitando duplicados por tildes/formato."""
    if not name:
        return ''
    txt = unicodedata.normalize('NFKD', name).encode(
        'ascii', 'ignore').decode()
    txt = re.sub(r'[^A-Za-z0-9 ]', ' ', txt).upper()
    return re.sub(r'\s+', ' ', txt).strip()


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number', required=True,
                                 help="The Port Number of the Device")
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the partner')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda
                                     self: self.env.user.company_id.id,
                                 help='Current Company')

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30,
                password=0, ommit_ping=True)
        try:
            if zk.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Connected',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Exception as error:
            raise ValidationError(f'{error}')

    def action_set_timezone(self):
        """Function to set user's timezone to device"""
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=True)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                user_tz = self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC'
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz))
                conn.set_time(user_timezone_time)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Set the Time',
                        'type': 'success',
                        'sticky': False
                    }
                }
            else:
                raise UserError(_(
                    "Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(machine_ip, port=zk_port, timeout=30,
                            password=0, force_udp=False, ommit_ping=True)
                except NameError:
                    raise UserError(_(
                        "Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute(
                            """delete from zk_machine_attendance""")
                        conn.disconnect()
                    else:
                        raise UserError(
                            _('Unable to clear Attendance log.Are you sure '
                              'attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use '
                          'Test Connection button to verify.'))
            except Exception as error:
                raise ValidationError(f'{error}')

    @api.model
    def cron_download(self):
        machines = self.env['biometric.device.details'].search([])
        for machine in machines:
            machine.action_download_attendance()

    def action_open_download_wizard(self):
        """Open a wizard so the user can pick a date range before downloading.

        This is the action bound to the *Download Data* button in the form
        view; the actual work is done by :meth:`action_download_attendance`,
        which the wizard calls after the user confirms.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Download Attendance'),
            'res_model': 'biometric.download.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'biometric.device.details',
                'default_device_id': self.id,
            },
        }

    def action_download_attendance(self, date_from=None, date_to=None):
        """Download attendance records from the device.

        :param date_from: optional ``date`` (inclusive) - events whose
            device timestamp falls before this date are skipped.
        :param date_to: optional ``date`` (inclusive) - events whose
            device timestamp falls after this date are skipped.

        Fixes applied (Crossnexion):
          * Optional date range filter (``date_from`` / ``date_to``).
          * Events are sorted chronologically before processing.
          * check_out is only written when the open check_in is earlier.
          * The dangerous "write to last attendance by id" fallback was
            replaced by logging + keeping the raw event only.
          * Duplicate/consecutive check-ins are logged.
        """
        # Normalise date args (may arrive as string from RPC/wizard)
        if isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)
        if isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)
        _logger.info(
            "++++++++++++ ZK Attendance download started "
            "(range: %s -> %s) ++++++++++++", date_from, date_to)

        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=True)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      " with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            self.action_set_timezone()
            if not conn:
                raise UserError(_('Unable to connect, please check the'
                                  ' parameters and network connections.'))
            conn.disable_device()
            try:
                user = conn.get_users()
                attendance = conn.get_attendance()
                if not attendance:
                    raise UserError(_('Unable to get the attendance log, please'
                                      ' try again later.'))

                # --- FIX 1: chronological processing --------------------
                try:
                    attendance = sorted(
                        attendance, key=lambda a: a.timestamp)
                except Exception as sort_err:
                    _logger.warning(
                        "ZK attendance: could not sort events (%s). "
                        "Continuing with device order.", sort_err)

                # --- FIX 2: optional date range filter -----------------
                if date_from or date_to:
                    before = len(attendance)
                    attendance = [
                        a for a in attendance
                        if (not date_from or a.timestamp.date() >= date_from)
                        and (not date_to or a.timestamp.date() <= date_to)
                    ]
                    _logger.info(
                        "ZK attendance: date filter kept %d of %d events "
                        "(%s -> %s).",
                        len(attendance), before, date_from, date_to)
                    if not attendance:
                        _logger.info(
                            "ZK attendance: no events in the selected range.")
                        return True

                user_by_id = {u.user_id: u for u in user}
                local_tz = pytz.timezone(
                    self.env.user.partner_id.tz or 'GMT')

                # --- FIX (Crossnexion): indices para NO duplicar empleados --
                Employee = self.env['hr.employee']
                ZkUser = self.env['hr.zk.device.user']
                # Nombre normalizado -> empleado (solo activos). Se usa para
                # emparejar por nombre cuando el ID del reloj no coincide con
                # ningun empleado existente, evitando crear un duplicado.
                emp_by_norm = {}
                for emp in Employee.search([], order='id asc'):
                    emp_by_norm.setdefault(_normalize_name(emp.name), emp)

                # Crossnexion: ya NO se crea un hr.attendance por cada par
                # in/out. Se capturan los fichajes crudos (zk.machine.attendance)
                # y luego se reconstruye UNA marcacion por (empleado, dia) desde
                # el crudo (ignorando los fichajes intermedios de descanso). Aqui
                # solo registramos a quien y que rango de fechas se afecto.
                affected_emp_ids = set()
                min_punch_utc = None
                max_punch_utc = None

                for each in attendance:
                    # Device local time -> UTC
                    try:
                        local_dt = local_tz.localize(
                            each.timestamp, is_dst=None)
                    except Exception:
                        local_dt = local_tz.localize(
                            each.timestamp, is_dst=False)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    atten_time = fields.Datetime.to_string(
                        utc_dt.replace(tzinfo=None))

                    device_user = user_by_id.get(each.user_id)
                    if not device_user:
                        _logger.info(
                            "ZK attendance: event for unknown device user "
                            "%s at %s ignored.", each.user_id, atten_time)
                        continue

                    # --- FIX (Crossnexion): NO duplicar empleados ----------
                    # El ID del reloj puede llegar como int o con espacios; lo
                    # normalizamos a string. Buscamos al empleado en este
                    # orden y SOLO creamos si no aparece por ninguna via:
                    #   1) Mapeo de IDs de reloj (varios IDs por empleado).
                    #   2) device_id_num (ID principal heredado).
                    #   3) Nombre normalizado exacto entre activos.
                    device_uid = str(each.user_id).strip()
                    device_name = (device_user.name or '').strip()

                    mapping = ZkUser.search(
                        [('device_uid', '=', device_uid)], limit=1)
                    get_user_id = mapping.employee_id
                    if not get_user_id:
                        get_user_id = Employee.search(
                            [('device_id_num', '=', device_uid)],
                            order='id asc', limit=1)
                    if not get_user_id and device_name:
                        get_user_id = emp_by_norm.get(
                            _normalize_name(device_name)) or Employee.browse()
                    if not get_user_id:
                        get_user_id = Employee.create({
                            'device_id_num': device_uid,
                            'name': device_name or _('Empleado %s') % device_uid,
                        })
                        emp_by_norm.setdefault(
                            _normalize_name(get_user_id.name), get_user_id)
                        _logger.info(
                            "ZK attendance: empleado creado para device id "
                            "%s (%s).", device_uid, get_user_id.name)
                    # Registrar el ID del reloj en el mapeo (idempotente) y
                    # completar device_id_num si estaba vacio. NO se pisa el
                    # nombre del empleado (el del reloj suele venir abreviado).
                    if not mapping:
                        ZkUser._register_uid(
                            device_uid, get_user_id, device_name)
                    if not get_user_id.device_id_num:
                        get_user_id.device_id_num = device_uid

                    # Crossnexion: registrar empleado y rango afectado para la
                    # reconstruccion posterior (una marcacion por dia). Se hace
                    # ANTES del control de duplicados para que un dia con
                    # fichajes ya capturados igual se reconstruya.
                    affected_emp_ids.add(get_user_id.id)
                    punch_dt = utc_dt.replace(tzinfo=None)
                    if min_punch_utc is None or punch_dt < min_punch_utc:
                        min_punch_utc = punch_dt
                    if max_punch_utc is None or punch_dt > max_punch_utc:
                        max_punch_utc = punch_dt

                    duplicate_atten_ids = zk_attendance.search([
                        ('device_id_num', '=', device_uid),
                        ('punching_time', '=', atten_time),
                    ], limit=1)
                    if duplicate_atten_ids:
                        continue

                    zk_attendance.create({
                        'employee_id': get_user_id.id,
                        'device_id_num': device_uid,
                        'attendance_type': str(each.status),
                        'punch_type': str(each.punch),
                        'punching_time': atten_time,
                        'address_id': info.address_id.id,
                    })

                    # Crossnexion: el emparejamiento in/out ya NO se hace aqui.
                    # El fichaje quedo guardado en el registro crudo
                    # (zk.machine.attendance); la marcacion hr.attendance se
                    # reconstruye despues del bucle (una por empleado/dia).

                # Crossnexion: reconstruir hr.attendance = UNA marcacion por
                # (empleado, dia) desde el registro crudo. Los fichajes
                # intermedios de desayuno/almuerzo ya NO generan marcaciones
                # incompletas; el descanso se descuenta solo (cae dentro del
                # tramo [primera entrada, ultima salida]).
                if min_punch_utc is not None:
                    self._zk_rebuild_attendances(
                        min_punch_utc, max_punch_utc,
                        employee_ids=list(affected_emp_ids))

                # Crossnexion: regenerar tablero diario y recomputar
                # shift_lines automaticamente despues de descargar.
                self._post_download_recompute(date_from, date_to)
                return True
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except Exception:
                    pass


    # ------------------------------------------------------------------
    # Crossnexion: reconstruccion de hr.attendance desde el registro crudo.
    # UNA marcacion por (empleado, dia) = [primer fichaje, ultima salida].
    # ------------------------------------------------------------------
    def _zk_employee_tz(self, employee):
        """Zona horaria del empleado (cae a la del usuario o America/Asuncion)."""
        tz_name = (
            (employee.tz if employee else False)
            or (employee.resource_calendar_id.tz
                if employee and employee.resource_calendar_id else False)
            or self.env.user.tz or 'America/Asuncion'
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone('America/Asuncion')

    def _zk_rebuild_attendances(self, dt_from_utc, dt_to_utc, employee_ids=None):
        """Reconstruye hr.attendance desde zk.machine.attendance.

        Crea UNA marcacion por (empleado, dia local) = [primer fichaje,
        ultima salida], ignorando los fichajes intermedios de descanso. El
        descanso (Desayuno/Almuerzo) queda dentro de ese tramo y se descuenta
        solo via las franjas del turno, marque o no marque el empleado.

        Reglas:
          * check_in  = primer fichaje del dia.
          * check_out = ultimo fichaje del dia cuando hay 2 o mas fichajes.
            NO se usa el punch_type del reloj porque no es confiable (a veces
            marca todos los fichajes como "Check In"). Si hay un solo fichaje
            en el dia, la marcacion queda SIN check_out -> aparece en
            "Correccion de Marcaciones" para corregir la salida.
          * Idempotente: si el dia ya tiene una marcacion corregida a mano
            (manually_corrected=True) NO se toca.
          * Pensado para jornadas diurnas (un dia calendario).

        :return: dict con conteos (created/updated/skipped/groups).
        """
        Raw = self.env['zk.machine.attendance'].sudo()
        # Contexto zk_rebuild=True: evita que el write marque la marcacion
        # como "corregida a mano" (eso es solo para ediciones de usuario).
        HrAtt = self.env['hr.attendance'].with_context(zk_rebuild=True).sudo()
        domain = [
            ('punching_time', '>=', dt_from_utc),
            ('punching_time', '<=', dt_to_utc),
            ('employee_id', '!=', False),
            ('punching_time', '!=', False),
        ]
        if employee_ids:
            domain.append(('employee_id', 'in', employee_ids))
        raws = Raw.search(domain, order='punching_time asc')
        if not raws:
            return {'created': 0, 'updated': 0, 'skipped': 0, 'groups': 0}

        # Agrupar por (empleado, dia local)
        emp_tz = {}
        groups = {}
        for r in raws:
            emp = r.employee_id
            tz = emp_tz.get(emp.id)
            if tz is None:
                tz = self._zk_employee_tz(emp)
                emp_tz[emp.id] = tz
            local = pytz.utc.localize(r.punching_time).astimezone(tz)
            key = (emp.id, local.date())
            groups.setdefault(key, []).append(
                (r.punching_time, str(r.punch_type or '')))

        has_flag = 'manually_corrected' in HrAtt._fields
        created = skipped = 0
        for (emp_id, day), punches in sorted(
                groups.items(), key=lambda x: (x[0][0], x[0][1])):
            punches.sort(key=lambda p: p[0])
            times = [p[0] for p in punches]

            tz = emp_tz[emp_id]
            day_start = tz.localize(datetime.datetime.combine(
                day, datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            day_end = tz.localize(datetime.datetime.combine(
                day, datetime.time.max)).astimezone(pytz.utc).replace(tzinfo=None)
            existing = HrAtt.search([
                ('employee_id', '=', emp_id),
                ('check_in', '>=', day_start),
                ('check_in', '<=', day_end),
            ], order='check_in asc')
            # No se tocan los dias con alguna marcacion corregida a mano.
            if has_flag and existing and any(existing.mapped('manually_corrected')):
                skipped += 1
                continue

            # UNA marcacion por (empleado, dia) = [primer fichaje, ultimo].
            # Los huecos a mitad de dia (el empleado salio y volvio) NO parten la
            # jornada: "corren directo" (cuentan como presentes). El descuento de
            # un hueco se maneja SOLO si hay un permiso/tiempo personal aprobado
            # (no se asume ausencia aqui). Los descansos (desayuno/almuerzo) se
            # descuentan via las franjas del turno; la tardanza y la salida
            # temprana surgen de que el primer/ultimo fichaje no cubran las
            # franjas ordinarias. El punch_type del reloj NO se usa (no es
            # confiable). check_out = ultimo fichaje; si hay un solo fichaje en el
            # dia, queda SIN salida (incompleto a corregir en entrada/salida).
            check_out = times[-1] if len(times) > 1 else False
            if existing:
                existing.unlink()
            HrAtt.create({
                'employee_id': emp_id,
                'check_in': times[0],
                'check_out': check_out,
            })
            created += 1
        _logger.info(
            "ZK rebuild: %d grupos (emp,dia) -> %d marcaciones creadas, "
            "%d dias saltados (corregidos a mano).",
            len(groups), created, skipped)
        return {'created': created, 'skipped': skipped, 'groups': len(groups)}

    # ------------------------------------------------------------------
    # Crossnexion: hook automatico despues de descargar marcaciones.
    # Regenera el tablero diario y recomputa las shift_lines del periodo
    # descargado, si los modelos de hr_attendance_shift_groups estan
    # disponibles. Si no, no hace nada (compatibilidad).
    # ------------------------------------------------------------------
    def _post_download_recompute(self, date_from=None, date_to=None):
        """Disparado despues de action_download_attendance. Llama
        automaticamente a:
          1. hr.attendance.daily.report.regenerate(date_from, date_to)
          2. hr.attendance._recompute_shift_lines() de las marcaciones
             del periodo
        Solo si esos modelos/metodos estan disponibles (i.e.
        hr_attendance_shift_groups instalado)."""
        try:
            DailyReport = self.env.get('hr.attendance.daily.report')
            if DailyReport is not None and hasattr(DailyReport, 'regenerate'):
                df = date_from
                dt = date_to
                if not df or not dt:
                    today = fields.Date.context_today(self)
                    df = df or today.replace(day=1)
                    dt = dt or today
                count = DailyReport.regenerate(date_from=df, date_to=dt)
                _logger.info(
                    "Post-download: regenerate genero %d filas en daily report.",
                    count or 0)
        except Exception as e:
            _logger.warning("Post-download regenerate fallo: %s", e)

        try:
            Att = self.env.get('hr.attendance')
            if Att is not None and hasattr(Att, '_recompute_shift_lines'):
                domain = []
                if date_from:
                    domain.append(('check_in', '>=',
                                   fields.Datetime.to_datetime(date_from)))
                if date_to:
                    end_dt = fields.Datetime.to_datetime(date_to)
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    domain.append(('check_in', '<=', end_dt))
                atts = Att.search(domain) if domain else Att.search([])
                if atts:
                    atts._recompute_shift_lines()
                    _logger.info(
                        "Post-download: _recompute_shift_lines aplicado a %d "
                        "asistencias.", len(atts))
        except Exception as e:
            _logger.warning("Post-download _recompute_shift_lines fallo: %s", e)

    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=15,
                password=0,
                force_udp=False, ommit_ping=True)
        self.device_connect(zk).restar