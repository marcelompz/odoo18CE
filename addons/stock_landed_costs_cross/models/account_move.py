# -*- coding: utf-8 -*-
"""
Created on 2025-03-26 09:01:00

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ACcountMoveInherit(models.Model):
    _inherit = 'account.move'

    def action_view_landed_costs(self):
        """ 
        Devuelve una acción que muestra los costes de destino de la factura seleccionada. 
        Si solo hay un coste de destino, abre la vista de formulario directamente.
        Si hay más de un coste de destino, abre la vista de arbol para seleccionar.
        """
        self.ensure_one()

        try:
            result = self.env["ir.actions.actions"]._for_xml_id('stock_landed_costs.action_stock_landed_cost')
        except ValueError:
            raise UserError("No se encontró la acción para mostrar los costos de destino.")

        result['context'] = dict(self.env.context, default_vendor_bill_id=self.id)

        # Obtener los IDs de los costes de destino
        landed_costs = self.landed_costs_ids.ids

        if not landed_costs:
            result['domain'] = [('id', 'in', [])]  # Evita que muestre registros no deseados

        elif len(landed_costs) == 1:
            form_view = self.env.ref('stock_landed_costs.view_stock_landed_cost_form', False)
            if form_view:
                result.update({
                    'views': [(form_view.id, 'form')],
                    'res_id': landed_costs[0]
                })

        else:
            result['domain'] = [('id', 'in', landed_costs)]

        return result
