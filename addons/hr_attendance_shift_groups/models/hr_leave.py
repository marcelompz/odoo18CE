# -*- coding: utf-8 -*-
"""Extension de hr.leave para regenerar automaticamente el Tablero Diario
cuando se aprueba o rechaza una licencia."""
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _cn_regenerate_daily_report(self):
        """Regenera las filas del Tablero Diario para el rango y empleado
        de cada licencia. Usado tras aprobar/rechazar para reflejar
        el cambio de estado en el Tablero."""
        Report = self.env['hr.attendance.daily.report'].sudo()
        for leave in self:
            if not leave.employee_id or not leave.date_from or not leave.date_to:
                continue
            try:
                df = leave.date_from
                dt = leave.date_to
                if hasattr(df, 'date'):
                    df = df.date()
                if hasattr(dt, 'date'):
                    dt = dt.date()
                Report.regenerate(
                    date_from=df,
                    date_to=dt,
                    employee_ids=[leave.employee_id.id],
                )
            except Exception as e:
                _logger.warning(
                    "No se pudo regenerar el Tablero Diario tras "
                    "cambio de estado de hr.leave id=%d: %s", leave.id, e)

    def action_validate(self, *args, **kwargs):
        result = super().action_validate(*args, **kwargs)
        # Tras validacion exitosa, regenerar el Tablero del rango afectado
        self._cn_regenerate_daily_report()
        return result

    def action_refuse(self, *args, **kwargs):
        result = super().action_refuse(*args, **kwargs)
        # Tras rechazo, regenerar igual para que las filas vuelvan a 'absence'
        self._cn_regenerate_daily_report()
        return result

    def action_approve(self, *args, **kwargs):
        # En Odoo 18 algunas configuraciones llaman action_approve antes
        # de action_validate. Regenerar tambien aqui por si acaso.
        result = super().action_approve(*args, **kwargs)
        validated = self.filtered(lambda l: l.state == 'validate')
        validated._cn_regenerate_daily_report()
        return result
