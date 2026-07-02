# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import timedelta

from odoo import api, models


class ReportShiftDashboard(models.AbstractModel):
    _name = 'report.hr_attendance_shift_groups.report_shift_dashboard'
    _description = 'Reporte PDF: Tablero por Turnos'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['hr.attendance.shift.export'].browse(docids)
        wizard.ensure_one()
        payload = wizard._collect_data()

        # Agrupar por shift_group para pintar una sección por grupo
        groups = {}
        for row in payload['rows']:
            g = row['shift_group']
            if not g:
                continue
            if g.id not in groups:
                groups[g.id] = {
                    'group': g,
                    'slots': g.get_visible_slots(),
                    'rows': [],
                }
            groups[g.id]['rows'].append(row)

        # Lista de fechas
        dates = []
        d = payload['date_from']
        while d <= payload['date_to']:
            dates.append(d)
            d += timedelta(days=1)

        return {
            'doc_ids': docids,
            'doc_model': 'hr.attendance.shift.export',
            'docs': wizard,
            'groups': list(groups.values()),
            'dates': dates,
            'date_from': payload['date_from'],
            'date_to': payload['date_to'],
            'company': payload['company'],
        }
