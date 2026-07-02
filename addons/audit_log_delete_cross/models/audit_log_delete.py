# -*- coding: utf-8 -*-
"""
Created on 2025-08-14 18:16:49

@author: drojo
"""
# python
import logging
import json

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AuditLogDelete(models.Model):
    _name = 'audit.log.delete'
    _description = 'Registro de Auditoría de Eliminaciones'
    _order = 'deletion_date desc'
    _log_access = False # Para que el propio log no se loguee a sí mismo

    model_name = fields.Char(
        string='Modelo', readonly=True, index=True)
    res_id = fields.Integer(
        string='ID del Registro', readonly=True)
    display_name = fields.Char(
        string='Nombre del Registro', readonly=True)
    user_id = fields.Many2one(
        'res.users', string='Eliminado por', readonly=True)
    deletion_date = fields.Datetime(
        string='Fecha de Eliminación', default=fields.Datetime.now, readonly=True)
    data_dump = fields.Text(
        string='Datos Eliminados (JSON)', readonly=True)

    def view_data_dump_pretty(self):
        """Devuelve el JSON formateado para una mejor visualización."""
        self.ensure_one()
        try:
            parsed_json = json.loads(self.data_dump)
            return json.dumps(parsed_json, indent=4, sort_keys=True, default=str)
        except (json.JSONDecodeError, TypeError):
            return self.data_dump
