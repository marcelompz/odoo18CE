# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BiometricDownloadWizard(models.TransientModel):
    """Wizard to download biometric device attendance filtered by date range."""
    _name = 'biometric.download.wizard'
    _description = 'Biometric Attendance Download Wizard'

    device_id = fields.Many2one(
        'biometric.device.details', string='Device', required=True,
        help='Biometric device from which to download attendance events.')
    date_from = fields.Date(
        string='From',
        help='Only events from this date (inclusive) will be imported. '
             'Leave empty to download from the beginning.')
    date_to = fields.Date(
        string='To',
        help='Only events up to this date (inclusive) will be imported. '
             'Leave empty to download up to the latest event.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_id and active_model == 'biometric.device.details':
            res['device_id'] = active_id
        # Default to today's range for convenience
        today = fields.Date.context_today(self)
        res.setdefault('date_from', today)
        res.setdefault('date_to', today)
        return res

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from and wiz.date_to and wiz.date_from > wiz.date_to:
                raise ValidationError(
                    _("'From' date cannot be later than 'To' date."))

    def action_confirm(self):
        """Trigger the download on the selected device with the date filter."""
        self.ensure_one()
        self.device_id.action_download_attendance(
            date_from=self.date_from, date_to=self.date_to)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attendance'),
                'message': _('Download completed for the selected range.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
