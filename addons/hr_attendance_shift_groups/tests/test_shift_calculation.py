# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestShiftCalculation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Group = cls.env['hr.shift.group']
        cls.Slot = cls.env['hr.shift.slot']
        cls.Employee = cls.env['hr.employee']
        cls.Attendance = cls.env['hr.attendance']

        # Use UTC employee tz to make tests deterministic
        cls.employee = cls.Employee.create({
            'name': 'Test Worker',
            'tz': 'UTC',
        })
        cls.group_admin = cls.env.ref('hr_attendance_shift_groups.shift_group_administrativo')
        cls.group_oper = cls.env.ref('hr_attendance_shift_groups.shift_group_operativo')
        cls.employee.shift_group_id = cls.group_admin.id

    # ----------------------------------------------------------------------
    # Validaciones de configuración
    # ----------------------------------------------------------------------
    def test_01_group_must_have_slots(self):
        new_group = self.Group.create({'name': 'Vacío'})
        # con slots vacíos al guardar/validar:
        with self.assertRaises(ValidationError):
            new_group._check_slots()

    def test_02_overlap_detection(self):
        new_group = self.Group.create({'name': 'Solapado'})
        self.Slot.create({
            'shift_group_id': new_group.id, 'name': 'A',
            'time_from': 8.0, 'time_to': 12.0, 'slot_type': 'ordinary',
        })
        self.Slot.create({
            'shift_group_id': new_group.id, 'name': 'B',
            'time_from': 11.0, 'time_to': 13.0, 'slot_type': 'ordinary',
        })
        with self.assertRaises(ValidationError):
            new_group._check_slots()

    def test_03_midnight_crossing_flag(self):
        slot = self.group_admin.slot_ids.filtered(lambda s: s.slot_type == 'extra_night')
        self.assertTrue(slot, 'No se encontró la franja extra nocturna en grupo admin demo')
        self.assertTrue(all(s.crosses_midnight for s in slot))

    # ----------------------------------------------------------------------
    # Cálculo de distribución
    # ----------------------------------------------------------------------
    def _create_attendance(self, dt_in, dt_out):
        return self.Attendance.create({
            'employee_id': self.employee.id,
            'check_in': dt_in,
            'check_out': dt_out,
        })

    def test_10_admin_normal_workday(self):
        """Empleado administrativo, jornada 07:00 - 17:00."""
        att = self._create_attendance(datetime(2025, 4, 1, 7, 0), datetime(2025, 4, 1, 17, 0))
        # Esperado: 5h Diurno + 1h Almuerzo + 4h Tarde = 9h ordinarias + 1h descanso
        self.assertAlmostEqual(att.hours_ordinary, 9.0, places=2)
        self.assertAlmostEqual(att.hours_break, 1.0, places=2)
        self.assertAlmostEqual(att.hours_extra_day, 0.0, places=2)
        self.assertAlmostEqual(att.hours_extra_night, 0.0, places=2)

    def test_11_admin_with_extra_day(self):
        """Empleado administrativo, 07:00 - 19:00 (1h ordinario tarde + 2h extra)."""
        att = self._create_attendance(datetime(2025, 4, 1, 7, 0), datetime(2025, 4, 1, 19, 0))
        # Ordinario = 5 (mañana) + 4 (tarde) = 9; Almuerzo descontado = 1; Extra = 17:00 -> 19:00 = 2h
        self.assertAlmostEqual(att.hours_ordinary, 9.0, places=2)
        self.assertAlmostEqual(att.hours_extra_day, 2.0, places=2)
        self.assertAlmostEqual(att.hours_break, 1.0, places=2)

    def test_12_admin_extra_night_crossing_midnight(self):
        """Trabaja 18:00 - 02:00 del día siguiente."""
        att = self._create_attendance(datetime(2025, 4, 1, 18, 0), datetime(2025, 4, 2, 2, 0))
        # Extra Diurno: 18:00-20:00 = 2h
        # Extra Nocturno: 20:00-02:00 = 6h
        self.assertAlmostEqual(att.hours_extra_day, 2.0, places=2)
        self.assertAlmostEqual(att.hours_extra_night, 6.0, places=2)

    def test_13_oper_with_breakfast_lunch_breaks(self):
        """Empleado operativo, 06:30 - 17:00. Descanso 40min desayuno + 1h20min almuerzo."""
        self.employee.shift_group_id = self.group_oper.id
        att = self._create_attendance(datetime(2025, 4, 1, 6, 30), datetime(2025, 4, 1, 17, 0))
        # Total bruto = 10.5h
        # Desayuno: 40min = 0.6667h
        # Almuerzo: 1h20min = 1.3333h
        # Ordinario: Entrada (6:30-7:30)=1h + Diurno(8:10-11:40)=3.5h + Tarde(13-17)=4h = 8.5h
        self.assertAlmostEqual(att.hours_ordinary, 8.5, places=2)
        self.assertAlmostEqual(att.hours_break, 2.0, places=2)
        self.assertAlmostEqual(att.hours_extra_day, 0.0, places=2)

    def test_14_oper_early_arrival_extra_day(self):
        """Operativo entra 06:00 (30 min de extra madrugada)."""
        self.employee.shift_group_id = self.group_oper.id
        att = self._create_attendance(datetime(2025, 4, 1, 6, 0), datetime(2025, 4, 1, 17, 0))
        self.assertAlmostEqual(att.hours_extra_day, 0.5, places=2)

    def test_15_recompute_after_group_change(self):
        att = self._create_attendance(datetime(2025, 4, 1, 7, 0), datetime(2025, 4, 1, 17, 0))
        old_lines = len(att.shift_line_ids)
        self.assertGreater(old_lines, 0)
        # Cambiar grupo de turno y recalcular
        self.employee.shift_group_id = self.group_oper.id
        att.shift_group_id = self.group_oper.id
        att._recompute_shift_lines()
        self.assertGreater(len(att.shift_line_ids), 0)
        # Para operativo, 7:00-17:00 cae en Entrada(0.5)+Desayuno+Diurno+Almuerzo+Tarde
        # ordinario = 0.5 + 3.5 + 4 = 8h
        self.assertAlmostEqual(att.hours_ordinary, 8.0, places=2)
