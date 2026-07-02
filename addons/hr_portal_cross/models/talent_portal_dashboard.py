# -*- coding: utf-8 -*-
"""
Dashboard de KPIs del portal Talento Humano.
Modelo TransientModel-like con campos calculados al vuelo.
"""
from datetime import date

from odoo import _, api, fields, models


class TalentPortalDashboard(models.AbstractModel):
    _name = 'talent.portal.dashboard'
    _description = 'Dashboard KPIs Talento Humano'

    @api.model
    def get_kpis(self):
        """Retorna un dict con los conteos clave para el dashboard."""
        kpis = {
            'leaves_to_approve': 0,
            'advances_to_approve': 0,
            'loans_to_approve': 0,
            'payslips_draft': 0,
            'birthdays_today': 0,
            'birthdays_month': 0,
            'employees_total': 0,
        }
        Leave = self.env['hr.leave'].sudo()
        kpis['leaves_to_approve'] = Leave.search_count([
            ('state', 'in', ('confirm', 'validate1')),
        ])

        if 'hr.advance' in self.env:
            Advance = self.env['hr.advance'].sudo()
            kpis['advances_to_approve'] = Advance.search_count([
                ('state', 'in', ('draft', 'rrhh_approved')),
            ])
        if 'hr.loan' in self.env:
            Loan = self.env['hr.loan'].sudo()
            kpis['loans_to_approve'] = Loan.search_count([
                ('state', 'in', ('draft', 'rrhh_approved')),
            ])

        if 'hr.payslip' in self.env:
            Payslip = self.env['hr.payslip'].sudo()
            kpis['payslips_draft'] = Payslip.search_count([('state', '=', 'draft')])

        # Cumpleaños
        Emp = self.env['hr.employee'].sudo()
        kpis['employees_total'] = Emp.search_count([('active', '=', True)])

        try:
            self.env.cr.execute("""
                SELECT COUNT(*) FROM hr_employee
                WHERE active = TRUE AND birthday IS NOT NULL
                  AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE)
            """)
            kpis['birthdays_month'] = self.env.cr.fetchone()[0] or 0

            self.env.cr.execute("""
                SELECT COUNT(*) FROM hr_employee
                WHERE active = TRUE AND birthday IS NOT NULL
                  AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE)
                  AND EXTRACT(DAY FROM birthday) = EXTRACT(DAY FROM CURRENT_DATE)
            """)
            kpis['birthdays_today'] = self.env.cr.fetchone()[0] or 0
        except Exception:
            pass

        return kpis
