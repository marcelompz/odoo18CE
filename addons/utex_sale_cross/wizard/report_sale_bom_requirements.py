# -*- coding: utf-8 -*-
"""
Created on 2025-11-27 11:45:50

@author: drojo
"""
# python
import logging
from collections import defaultdict

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ReportSaleBomRequirements(models.AbstractModel):
    _name = 'report.utex_sale_cross.report_sale_bom_req_template'
    _description = 'Reporte de Requerimientos de Materiales por Venta'

    def _get_report_values(self, docids, data=None):
        orders = self.env['sale.order'].browse(docids)
        
        # Diccionario acumulador
        materials_data = defaultdict(lambda: {'qty_needed': 0.0, 'product': None})

        for order in orders:
            for line in order.order_line:
                if line.display_type or not line.product_id:
                    continue
                
                # Llamamos a la función recursiva para cada línea de venta
                # Esta función llenará 'materials_data' mágicamente
                self._explode_recursive(
                    line.product_id, 
                    line.product_uom_qty, 
                    order.company_id.id, 
                    materials_data
                )

        # Preparar lista final (Igual que antes)
        final_list = []
        for pid, data in materials_data.items():
            product = data['product']
            qty_needed = data['qty_needed']
            
            qty_available = product.qty_available
            to_buy = max(0, qty_needed - qty_available)

            vendor_name = ''
            if product.seller_ids:
                last_seller = product.seller_ids[-1]
                vendor_name = last_seller.partner_id.name

            final_list.append({
                'product_name': product.display_name,
                'vendor_name': vendor_name,
                'uom_name': product.uom_id.name,
                'qty_needed': qty_needed,
                'qty_available': qty_available,
                'to_buy': to_buy,
            })

        final_list.sort(key=lambda x: x['product_name'])

        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': orders,
            'materials': final_list,
        }

    def _explode_recursive(self, product, qty, company_id, materials_data):
        """
        Función recursiva que busca la BoM.
        - Si tiene BoM: Explota y se llama a sí misma para cada componente.
        - Si NO tiene BoM: Es materia prima final, la agrega al reporte.
        """
        # Intentamos buscar una BoM para este producto
        bom = self.env['mrp.bom']._bom_find(product, company_id=company_id)[product]

        if not bom:
            # CASO BASE: No hay BoM (es Tela Sensitive, Hilo, o un producto comprado)
            # Agregamos a la lista final
            materials_data[product.id]['product'] = product
            materials_data[product.id]['qty_needed'] += qty
            return

        # CASO RECURSIVO: Tiene BoM (es Remera, Tela Frente, etc.)
        # Explotamos este nivel
        boms_done, lines_done = bom.explode(product, qty)
        
        for bom_line, line_data in lines_done:
            comp_product = bom_line.product_id
            comp_qty = line_data['qty']
            
            # ¡AQUÍ ESTÁ EL TRUCO!
            # En lugar de guardar 'comp_product', volvemos a llamar a esta misma función
            # para ver si este componente tiene a su vez otros componentes.
            self._explode_recursive(comp_product, comp_qty, company_id, materials_data)
