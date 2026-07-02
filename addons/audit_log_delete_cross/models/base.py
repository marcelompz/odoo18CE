# -*- coding: utf-8 -*-
"""
Created on 2025-08-14 18:18:46

@author: drojo
"""
# python
import logging
import json

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # Lista de modelos a ignorar para no llenar el log con datos irrelevantes.
    _log_deletion_blacklist = [
        'audit.log.delete',
        'ir.attachment',
        'mail.message',
        'bus.bus',
        'ir.ui.view', # Evitar logs durante actualizaciones de vistas
        'mail.followers',
        'ir.cron.progress',
    ]

    def unlink(self):
        if self._name in self._log_deletion_blacklist or self.env.context.get('audit_log_disabled'):
            return super().unlink()

        # Leemos los datos ANTES de intentar la eliminación.
        try:
            records_data = self.read(load=False)
        except Exception as e:
            _logger.error("No se pudieron leer los datos para el log de borrado del modelo %s. Error: %s", self._name, e)
            # Si no podemos leer, no podemos loguear, pero permitimos que el borrado continúe (y falle si debe).
            return super().unlink()

        # Intentamos la eliminación.
        try:
            result = super().unlink()
            # Si llegamos aquí, ¡la eliminación fue exitosa! Ahora podemos loguear.
            if records_data:
                log_vals_list = []
                for data in records_data:
                    display_name = data.get('display_name', data.get('name', f"Registro #{data['id']}"))
                    log_vals_list.append({
                        'model_name': self._name,
                        'res_id': data['id'],
                        'display_name': display_name,
                        'user_id': self.env.user.id,
                        'data_dump': json.dumps(data, indent=4, default=str),
                    })
                
                if log_vals_list:
                    self.env['audit.log.delete'].sudo().create(log_vals_list)
            
            return result

        except Exception as e:
            # Si super().unlink() falla (ej. por un ForeignKeyViolation),
            # simplemente relanzamos la excepción para que el usuario vea el error original de Odoo.
            # NO intentamos loguear nada, porque el registro NO fue eliminado.
            _logger.warning(
                "La eliminación para el modelo %s fue prevenida por una regla de negocio o error de base de datos. No se creará log de borrado. Error: %s",
                self._name, e
            )
            raise # <-- Relanzar la excepción original es crucial.
