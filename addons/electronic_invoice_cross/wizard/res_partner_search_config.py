# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:44:03

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
#_logger.info('Mesaje Test: %s', error) -> exception, error


class ResPartnerSearchConfig(models.Model):
    _name = 'res.partner.search.config'
    _description = 'Configuración del buscador de datos del contacto'
    _rec_name = 'db_name'
    
    db_name = fields.Char(
        string='DB Name')
    db_user = fields.Char(
        string='DB User')
    db_pwd = fields.Char(
        string='DB Password')
    db_host = fields.Char(
        string='DB Host')
    db_port = fields.Char(
        string='DB Port')

    def action_save(self):
        """Guarda los cambios en el registro y cierra la ventana."""
        # Guardar los cambios en el registro actual
        self.ensure_one()  # Asegura que solo hay un registro en el contexto
        self.write(self._context.get('default_vals', {}))  # Guarda cambios (si hay valores específicos en el contexto)

        # Cierra la ventana
        return {'type': 'ir.actions.act_window_close'}

