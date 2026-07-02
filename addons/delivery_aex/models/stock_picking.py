# -*- coding: utf-8 -*-
"""
Created on 2025-07-18 11:02:38

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def action_print_aex_label(self):
        """
        Acción del botón para llamar al método de impresión del transportista AEX.
        """
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != 'aex':
            raise UserError(_("Esta acción solo está disponible para envíos con el transportista AEX."))
            
        # Llamamos a la función que hemos creado en el delivery.carrier
        self.carrier_id.aex_print_label(self)

        # Devolvemos una acción para recargar la vista actual
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            # 'target': 'new',
        }

        # Devolvemos una acción de notificación para dar feedback al usuario
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': _('Impresión Exitosa'),
        #         'message': _('La etiqueta de AEX ha sido solicitada y se añadirá a los adjuntos en breve.'),
        #         'sticky': False,
        #         'type': 'success',
        #     }
        # }
