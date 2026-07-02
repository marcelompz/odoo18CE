import pytz
import xlsxwriter
import base64
import logging
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from io import BytesIO
from datetime import datetime, timedelta
from pytz import timezone
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class MsStockReportWizard(models.Model):
    _inherit = 'ms.stock.report.wizard'

    # Se mantiene, pero la lógica de stock a fecha la manejará get_current_stock_data completamente.
    # Esta función ahora solo es relevante si NO hay date_end.
    def _get_quant_ids(self):
        criteria = [
            ('location_id.usage', 'in', ['internal', 'transit']),
            '|',
            ('location_id.company_id', 'child_of', self.env.companies.ids),
            ('location_id.company_id', '=', False),
        ]
        if self.product_ids:
            criteria += [('product_id', 'in', self.product_ids.ids)]
        if self.lot_ids:
            criteria += [('lot_id', 'in', self.lot_ids.ids)]
        
        # Si se seleccionan ubicaciones, filtramos por ellas y sus hijos.
        # Si no se selecciona ninguna, se asume todas las ubicaciones internas/transit de la compañía.
        if self.location_ids:
            # Encuentra todas las ubicaciones hijas de las seleccionadas
            child_location_ids = self.env['stock.location'].search([
                ('id', 'child_of', self.location_ids.ids)
            ]).ids
            criteria += [('location_id', 'in', child_location_ids)]
        
        quant_ids = self.env['stock.quant'].search(criteria)
        return quant_ids

    def _get_product_cost_at_date(self, product, date_target):
        """
        Obtiene el costo unitario. Prioriza el historial si es una fecha pasada.
        Si es hoy, o si el historial falla/es cero, usa el costo estándar actual.
        """
        if not product:
            return 0.0

        if date_target >= fields.Date.today():
            return product.standard_price

        cost = 0.0
        date_target_dt = datetime.combine(date_target, datetime.max.time())
        
        if product.cost_method in ['fifo', 'average', 'last_in_first_out'] and product.valuation == 'real_time':
            valuation_layer = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id),
                ('create_date', '<=', date_target_dt),
                ('company_id', '=', self.env.company.id),
            ], order='create_date desc, id desc', limit=1)

            if valuation_layer:
                cost = valuation_layer.unit_cost

        if cost <= 0.0:
            cost = product.standard_price
            
        return cost

    def get_current_stock_data(self):
        datas = []
        
        # Preparar la lista de ubicaciones objetivo
        # Si self.location_ids está vacío, queremos considerar todas las ubicaciones internas/transit.
        # Si no, consideramos las seleccionadas y sus hijos.
        all_target_locations_ids = []
        if self.location_ids:
            all_target_locations_ids = self.env['stock.location'].search([
                ('id', 'child_of', self.location_ids.ids),
                ('usage', 'in', ['internal', 'transit']), # Solo ubicaciones de stock reales
                '|',
                ('company_id', 'child_of', self.env.companies.ids),
                ('company_id', '=', False),
            ]).ids
        else:
            # Si no hay ubicaciones seleccionadas, obtener todas las ubicaciones internas/transit.
            all_target_locations_ids = self.env['stock.location'].search([
                ('usage', 'in', ['internal', 'transit']),
                '|',
                ('company_id', 'child_of', self.env.companies.ids),
                ('company_id', '=', False),
            ]).ids

        # Convertir a set para búsquedas más rápidas
        all_target_locations_set = set(all_target_locations_ids)
        
        # Si hay una fecha fin, calculamos el stock hasta esa fecha.
        if self.date_end:
            target_date_end_dt = datetime.combine(self.date_end, datetime.max.time())
            
            move_line_criteria = [
                ('state', '=', 'done'), 
                ('picking_id.state', 'not in', ['cancel']), # No considerar movimientos de pickings cancelados
                ('date', '<=', target_date_end_dt),
            ]

            if self.product_ids:
                move_line_criteria += [('product_id', 'in', self.product_ids.ids)]
            if self.lot_ids:
                move_line_criteria += [('lot_id', 'in', self.lot_ids.ids)]
            
            # Filtro principal de ubicaciones para stock_move_line
            # Un movimiento es relevante si su origen O su destino están en las ubicaciones objetivo
            move_line_criteria += [
                '|',
                ('location_id', 'in', all_target_locations_ids),
                ('location_dest_id', 'in', all_target_locations_ids)
            ]
            
            stock_move_lines = self.env['stock.move.line'].search(move_line_criteria)

            stock_at_date = defaultdict(lambda: {
                'quantity': 0.0, 
                'incoming_date': None,     
                'product_id': None,
                'lot_id': None,
                'location_id': None, # La ubicación en la que se consolida este stock
            })

            # Reconstrucción del stock
            for sml in stock_move_lines:
                product_id = sml.product_id
                lot_id = sml.lot_id or self.env['stock.lot'] 

                # Es una entrada a una ubicación objetivo
                if sml.location_dest_id.id in all_target_locations_set:
                    # Si el origen es una ubicación objetivo Y el destino también,
                    # es una transferencia interna entre ubicaciones filtradas.
                    # En este caso, el stock "sale" de la origen y "entra" en el destino.
                    # Aseguramos que solo se registre en el destino para el reporte.
                    # Para el balance, restamos del origen y sumamos al destino.

                    # Sumamos al destino
                    key_dest = (product_id.id, lot_id.id, sml.location_dest_id.id)
                    stock_at_date[key_dest]['quantity'] += sml.qty_done
                    stock_at_date[key_dest]['product_id'] = product_id
                    stock_at_date[key_dest]['lot_id'] = lot_id
                    stock_at_date[key_dest]['location_id'] = sml.location_dest_id
                    # Para la fecha de entrada, tomamos la más reciente para cada "quant" histórico
                    if not stock_at_date[key_dest]['incoming_date'] or sml.date > stock_at_date[key_dest]['incoming_date']:
                        stock_at_date[key_dest]['incoming_date'] = sml.date
                
                # Es una salida de una ubicación objetivo
                if sml.location_id.id in all_target_locations_set:
                    # Restamos del origen
                    key_src = (product_id.id, lot_id.id, sml.location_id.id)
                    stock_at_date[key_src]['quantity'] -= sml.qty_done
                    stock_at_date[key_src]['product_id'] = product_id
                    stock_at_date[key_src]['lot_id'] = lot_id
                    stock_at_date[key_src]['location_id'] = sml.location_id
                    # No actualizamos incoming_date para salidas, solo para entradas.

            no = 1
            diff_hours = self._get_diff_hours() # Considera si realmente es necesario para fechas históricas
                                                # Odoo guarda fechas en UTC, la conversión es para display.
            for key, data in stock_at_date.items():
                # Solo incluimos los que tienen stock positivo a la fecha
                # if data['quantity'] > 0 and data['location_id']:
                if data['location_id']:
                    product = data['product_id']
                    location = data['location_id']

                    # Obtener el costo unitario del producto a la fecha_fin
                    unit_cost = self._get_product_cost_at_date(product, self.date_end)
                    total_cost = unit_cost * data['quantity'] if unit_cost else 0.0

                    # VENTAS Y MARGEN
                    sale_price = product.lst_price
                    total_sale_value = sale_price * data['quantity']
                    gross_margin = total_sale_value - total_cost
                    margin_percent = (gross_margin / total_sale_value) if total_sale_value != 0 else 0.0

                    incoming_date_str = ''
                    stock_age = 0
                    if data['incoming_date']:
                        # Convertir la fecha de entrada (UTC) a la zona horaria del usuario para mostrar
                        incoming_date_tz = pytz.UTC.localize(data['incoming_date']).astimezone(timezone(self.env.user.tz or 'UTC'))
                        incoming_date_str = incoming_date_tz.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Calcular la antigüedad con la fecha de fin del reporte como referencia
                        # Asegúrate de que ambas fechas tengan la misma zona horaria para la resta.
                        # target_date_end_dt ya está en el final del día en su zona (asumiendo local),
                        # para la resta, es mejor tenerlas en UTC si in_date es UTC.
                        stock_age_delta = target_date_end_dt.replace(tzinfo=pytz.UTC) - data['incoming_date'].replace(tzinfo=pytz.UTC)
                        stock_age = stock_age_delta.days if stock_age_delta.days >= 0 else 0

                    datas.append({
                        'no': no,
                        'product_name': product.display_name,
                        'categ_name': product.categ_id.name,
                        'lot_name': data['lot_id'].display_name if data['lot_id'] else '',
                        'location_name': data['location_id'].display_name,
                        'incoming_date': incoming_date_str,
                        'stock_age': stock_age,
                        'quantity': data['quantity'],
                        # Para stock histórico, calcular 'reserved_quantity' es más complejo y no trivial
                        # Odoo calcula reservaciones sobre quants actuales. A una fecha pasada,
                        # las reservaciones pueden no ser las mismas. Lo dejamos en 0 por defecto.
                        'reserved_quantity': 0.0, 
                        'available_quantity': data['quantity'], # Si no hay reserved_quantity, es el total
                        'unit_cost': unit_cost,
                        'total_cost': total_cost,
                        'sale_price': sale_price,
                        'total_sale_value': total_sale_value,
                        'gross_margin': gross_margin,
                        'margin_percent': margin_percent,
                    })
                    no += 1
        
        # Si NO hay fecha fin, volvemos al comportamiento original de stock.quant
        else:
            quant_ids = self._get_quant_ids() 
            _logger.info(f'total quant: {len(quant_ids)}, quant_ids: {quant_ids}')
            no = 1
            diff_hours = self._get_diff_hours() # Esto es para display, no para lógica de fechas
            for quant_id in quant_ids:
                product = quant_id.product_id
                
                # Obtener el costo unitario del producto actual
                unit_cost = self._get_product_cost_at_date(product, fields.Date.today()) # Fecha actual para stock actual
                total_cost = unit_cost * quant_id.quantity if unit_cost else 0.0

                # VENTAS Y MARGEN
                sale_price = product.lst_price
                total_sale_value = sale_price * quant_id.quantity
                gross_margin = total_sale_value - total_cost
                margin_percent = (gross_margin / total_sale_value) if total_sale_value != 0 else 0.0

                incoming_date = ''
                stock_age = 0
                if quant_id.in_date:
                    # Convertir la fecha de entrada (UTC) a la zona horaria del usuario
                    incoming_date_tz = pytz.UTC.localize(quant_id.in_date).astimezone(timezone(self.env.user.tz or 'UTC'))
                    incoming_date = incoming_date_tz.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Antigüedad respecto a la fecha actual
                    stock_age_delta = fields.Datetime.now(pytz.UTC) - quant_id.in_date.replace(tzinfo=pytz.UTC)
                    stock_age = stock_age_delta.days if stock_age_delta.days >= 0 else 0

                datas.append({
                    'no': no,
                    'product_name': product.display_name,
                    'categ_name': product.categ_id.name,
                    'lot_name': quant_id.lot_id.display_name or '',
                    'location_name': quant_id.location_id.display_name,
                    'incoming_date': incoming_date,
                    'stock_age': stock_age,
                    'quantity': quant_id.quantity,
                    'reserved_quantity': quant_id.reserved_quantity,
                    'available_quantity': quant_id.quantity - quant_id.reserved_quantity,
                    'unit_cost': unit_cost,
                    'total_cost': total_cost,
                    'sale_price': sale_price,
                    'total_sale_value': total_sale_value,
                    'gross_margin': gross_margin,
                    'margin_percent': margin_percent,
                })
                no += 1
        
        return datas

    def action_export_excel_current_stock(self, wbf, workbook):
        report_name = 'Stock actual'
        if self.date_end:
            report_name = f'Stock actual al {self.date_end.strftime("%Y-%m-%d")}'

        worksheet = workbook.add_worksheet(report_name)
        worksheet.merge_range('A2:P3', report_name, wbf['title_doc']) # Ajustar el rango de fusión para el título

        columns = [
            ('Nro', 5, 'no', 'no'),
            ('Producto', 50, 'char', 'char'),
            ('Categoría', 40, 'char', 'char'),
            ('Lote / SN', 20, 'char', 'char'),
            ('Ubicación', 40, 'char', 'char'),
            ('Fecha de entrada', 20, 'datetime', 'char'),
            ('Antigüedad (días)', 20, 'number', 'char'),
            ('Total', 20, 'float', 'float'),
            ('Reservado', 20, 'float', 'float'),
            ('Disponible', 20, 'float', 'float'),
            ('Costo Unitario', 20, 'float', 'float'),
            ('Costo Total', 20, 'float', 'float'),
            ('PVP Unit.', 15, 'float', 'float'),
            ('PVP Total', 15, 'float', 'float'),
            ('Margen Bruto', 15, 'float', 'float'),
            ('% Margen', 12, 'float', 'percent'),
        ]
        row = 4
        col = 0

        for column in columns:
            column_name = column[0]
            column_width = column[1]
            worksheet.set_column(col, col, column_width)
            col_alphabet = xlsxwriter.utility.xl_col_to_name(col)
            worksheet.write(f'{col_alphabet}{row}', column_name, wbf['header_orange'])

            col += 1

        row += 1

        datas = self.get_current_stock_data()
        first_row = end_row = row
        for data in datas:
            worksheet.write(f'A{row}', data['no'], wbf['content'])
            worksheet.write(f'B{row}', data['product_name'], wbf['content'])
            worksheet.write(f'C{row}', data['categ_name'], wbf['content'])
            worksheet.write(f'D{row}', data['lot_name'], wbf['content'])
            worksheet.write(f'E{row}', data['location_name'], wbf['content'])
            worksheet.write(f'F{row}', data['incoming_date'], wbf['content'])
            worksheet.write(f'G{row}', data['stock_age'], wbf['content_number'])
            worksheet.write(f'H{row}', data['quantity'], wbf['content_float'])
            worksheet.write(f'I{row}', data['reserved_quantity'], wbf['content_float'])
            worksheet.write(f'J{row}', data['available_quantity'], wbf['content_float'])
            worksheet.write(f'K{row}', data['unit_cost'], wbf['content_float'])
            worksheet.write(f'L{row}', data['total_cost'], wbf['content_float'])
            worksheet.write(f'M{row}', data['sale_price'], wbf['content_float'])
            worksheet.write(f'N{row}', data['total_sale_value'], wbf['content_float'])
            worksheet.write(f'O{row}', data['gross_margin'], wbf['content_float'])
            worksheet.write(f'P{row}', data['margin_percent'], wbf['content_percent'])
            end_row = row
            row += 1
        
        return wbf, workbook, worksheet, report_name, columns, row, first_row, end_row
