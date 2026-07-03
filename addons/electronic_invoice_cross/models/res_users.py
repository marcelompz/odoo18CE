# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:31:47

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    authorization_ids = fields.Many2many(
        'account.authorization', string='Timbrados predeterminados')

    def cross_user_notify(self, state='success', message=None, close=False, reload=False, sticky=False):
        # Crear la notificación inicial
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(message),
                'type': state,
                'sticky': sticky,
            },
        }

        # Si se debe cerrar la ventana actual
        if close:
            notification['params'].update({
                'next': {'type': 'ir.actions.act_window_close'},
            })

        # Si se debe recargar la vista
        if reload:
            notification['params'].update({
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            })

        return notification

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)

        copy_data = {
            'l10n_latam_identification_type_id': self.env.ref('l10n_py.it_vat'),
        }
        res.update(copy_data)
    
        return res
