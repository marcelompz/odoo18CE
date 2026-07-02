# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Antiguedad (en dias) del producto de la linea calculada como
    # MIN(stock_move.date) con location_id.usage='supplier' (1ra recepcion).
    # Si no hay recepcion registrada, cae a product.create_date.
    # Campo NO almacenado: se recalcula al leer las lineas. El _compute usa
    # un solo SQL para todos los products de las lineas que se estan
    # computando, por lo que es eficiente para listas grandes.
    dashboard_antiquity_days = fields.Integer(
        string="Antig. (días)",
        compute='_compute_dashboard_antiquity_days',
        store=False,
        help="Días desde la primera recepción del producto en stock. "
             "Si no hay recepciones, usa la fecha de creación del producto.",
    )

    @api.depends('product_id')
    def _compute_dashboard_antiquity_days(self):
        today = fields.Date.today()
        # Productos unicos en el set de lineas a computar
        products = self.mapped('product_id')
        pids = products.ids

        first_reception_map = {}
        if pids and 'stock.move' in self.env:
            try:
                self.env.cr.execute('''
                    SELECT sm.product_id, MIN(sm.date)::date AS first_recv
                    FROM stock_move sm
                    JOIN stock_location sl ON sl.id = sm.location_id
                    WHERE sm.state = 'done'
                      AND sl.usage = 'supplier'
                      AND sm.product_id IN %s
                    GROUP BY sm.product_id
                ''', (tuple(pids),))
                for row in self.env.cr.dictfetchall():
                    fr = row['first_recv']
                    if isinstance(fr, str):
                        fr = fields.Date.from_string(fr)
                    if fr:
                        first_reception_map[row['product_id']] = fr
            except Exception:
                first_reception_map = {}

        prod_antiquity = {}
        for prod in products:
            fr = first_reception_map.get(prod.id)
            if fr:
                prod_antiquity[prod.id] = max((today - fr).days, 0)
            elif prod.create_date:
                cd = prod.create_date
                if isinstance(cd, datetime.datetime):
                    cd = cd.date()
                prod_antiquity[prod.id] = max((today - cd).days, 0)
            else:
                prod_antiquity[prod.id] = 0

        for line in self:
            line.dashboard_antiquity_days = (
                prod_antiquity.get(line.product_id.id, 0)
                if line.product_id else 0
            )
