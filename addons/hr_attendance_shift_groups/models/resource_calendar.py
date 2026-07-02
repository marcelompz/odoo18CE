# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..hooks import _py_holidays_for_year, _create_one_holiday


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def action_load_paraguay_holidays(self):
        """Carga feriados de Paraguay en el(los) calendario(s) seleccionado(s)."""
        if not self:
            raise UserError(_('Seleccione al menos un calendario.'))
        return self._cn_load_py_holidays(self)

    @api.model
    def _cn_load_py_holidays(self, calendars):
        Leaves = self.env['resource.calendar.leaves'].sudo()
        years = range(2024, 2031)
        created = skipped = failed = 0
        for cal in calendars:
            for year in years:
                for d, name in _py_holidays_for_year(year):
                    r = _create_one_holiday(Leaves, cal.id, name, d)
                    if r == 'created':
                        created += 1
                    elif r == 'skipped':
                        skipped += 1
                    else:
                        failed += 1
        msg = _('Se crearon %d feriados nuevos; %d ya existian.') % (created, skipped)
        if failed:
            msg += _(' (%d fallaron por conflictos con feriados existentes)') % failed
        msg += _(' Recargue la pagina (F5) para ver los cambios.')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Feriados Paraguay actualizados'),
                'message': msg,
                'type': 'success' if not failed else 'warning',
                'sticky': True,
            },
        }


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    @api.model
    def action_load_py_holidays_all(self):
        """Carga feriados de Paraguay en TODOS los calendarios laborales."""
        Cal = self.env['resource.calendar'].sudo()
        calendars = Cal.search([])
        if not calendars:
            raise UserError(_('No hay calendarios laborales configurados.'))
        return Cal._cn_load_py_holidays(calendars)
