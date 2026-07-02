# -*- coding: utf-8 -*-
import base64
from datetime import datetime, date

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestExportXlsx(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env['hr.employee']
        cls.Attendance = cls.env['hr.attendance']
        cls.Wizard = cls.env['hr.attendance.shift.export']

        cls.group_admin = cls.env.ref('hr_attendance_shift_groups.shift_group_administrativo')
        cls.employee = cls.Employee.create({
            'name': 'Juan Perez',
            'tz': 'UTC',
            'shift_group_id': cls.group_admin.id,
        })
        cls.Attendance.create({
            'employee_id': cls.employee.id,
            'check_in': datetime(2025, 4, 1, 7, 0),
            'check_out': datetime(2025, 4, 1, 17, 0),
        })

    def test_01_export_generates_file(self):
        wiz = self.Wizard.create({
            'period_type': 'custom',
            'date_from': date(2025, 4, 1),
            'date_to': date(2025, 4, 30),
            'employee_ids': [(6, 0, [self.employee.id])],
            'include_empty_days': True,
        })
        wiz.action_export()
        self.assertTrue(wiz.file_data, 'No se generó archivo Excel')
        self.assertTrue(wiz.file_name.endswith('.xlsx'))
        # Validar que es un xlsx válido (zip header PK\x03\x04)
        content = base64.b64decode(wiz.file_data)
        self.assertEqual(content[:4], b'PK\x03\x04')
