import pytz
import xlsxwriter
import base64

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from io import BytesIO
from datetime import datetime
from pytz import timezone
from dateutil.relativedelta import relativedelta


class MsStockReportWizard(models.Model):
    _inherit = 'ms.stock.report.wizard'

    def _get_beginning_balance(self, product_id, lot_id):
        beginning_balance = 0
        if self.date_start:
            diff_hours = self._get_diff_hours()
            start_date = self.date_start.strftime('%d-%m-%Y 00:00:00')
            start_date = datetime.strptime(start_date, '%d-%m-%Y %H:%M:%S')
            start_date = start_date + relativedelta(hours=-diff_hours)
            print('\n start_date', start_date)
            move_line_in_criteria = [
                ('state', '=', 'done'),
                ('date', '<', start_date),
                ('product_id', '=', product_id.id),
                ('lot_id', '=', lot_id.id),
                ('location_dest_id', 'child_of', self.location_id.ids),
            ]
            move_line_out_criteria = [
                ('state', '=', 'done'),
                ('date', '<', start_date),
                ('product_id', '=', product_id.id),
                ('lot_id', '=', lot_id.id),
                ('location_id', 'child_of', self.location_id.ids),
            ]
            move_line_in_ids = self.env['stock.move.line'].search(move_line_in_criteria)
            move_line_out_ids = self.env['stock.move.line'].search(move_line_out_criteria)
            move_line_in_qty = 0
            move_line_out_qty = 0
            for move_line_in_id in move_line_in_ids:
                move_line_in_qty += product_id.uom_id._compute_quantity(
                    move_line_in_id.quantity, move_line_in_id.product_uom_id)
            for move_line_out_id in move_line_out_ids:
                move_line_out_qty += product_id.uom_id._compute_quantity(
                    move_line_out_id.quantity, move_line_out_id.product_uom_id)
            beginning_balance = move_line_in_qty - move_line_out_qty
        return beginning_balance

    def _get_move_line_in_ids(self, product_id, lot_id, start_date, end_date):
        move_line_in_criteria = [
            ('state', '=', 'done'),
            ('product_id', '=', product_id.id),
            ('lot_id', '=', lot_id.id),
            ('location_dest_id', 'child_of', self.location_id.ids),
        ]
        diff_hours = self._get_diff_hours()
        if start_date:
            start_date = start_date.strftime('%d-%m-%Y 00:00:00')
            start_date = datetime.strptime(start_date, '%d-%m-%Y %H:%M:%S')
            start_date = start_date + relativedelta(hours=-diff_hours)
            move_line_in_criteria += [('date', '>=', start_date)]
            print('\n start_date', start_date)
        if end_date:
            end_date = end_date.strftime('%d-%m-%Y 00:00:00')
            end_date = datetime.strptime(end_date, '%d-%m-%Y %H:%M:%S')
            end_date = end_date + relativedelta(hours=-diff_hours)
            move_line_in_criteria += [('date', '<=', end_date)]
            print('\n end_date', end_date)
        move_line_in_ids = self.env['stock.move.line'].search(move_line_in_criteria, order='date asc')
        return move_line_in_ids

    def _get_move_line_in_qty(self, product_id, lot_id, start_date, end_date):
        move_line_in_ids = self._get_move_line_in_ids(
            product_id=product_id,
            lot_id=lot_id,
            start_date=start_date,
            end_date=end_date
        )
        move_line_in_qty = 0
        for move_line_in_id in move_line_in_ids:
            move_line_in_qty += product_id.uom_id._compute_quantity(
                move_line_in_id.quantity, move_line_in_id.product_uom_id)
        return move_line_in_qty

    def _get_move_line_out_ids(self, product_id, lot_id, start_date, end_date):
        move_line_out_criteria = [
            ('state', '=', 'done'),
            ('product_id', '=', product_id.id),
            ('lot_id', '=', lot_id.id),
            ('location_id', 'child_of', self.location_id.ids),
        ]
        diff_hours = self._get_diff_hours()
        if start_date:
            start_date = start_date.strftime('%d-%m-%Y 00:00:00')
            start_date = datetime.strptime(start_date, '%d-%m-%Y %H:%M:%S')
            start_date = start_date + relativedelta(hours=-diff_hours)
            move_line_out_criteria += [('date', '>=', start_date)]
            print('\n start_date', start_date)
        if end_date:
            end_date = end_date.strftime('%d-%m-%Y 00:00:00')
            end_date = datetime.strptime(end_date, '%d-%m-%Y %H:%M:%S')
            end_date = end_date + relativedelta(hours=-diff_hours)
            move_line_out_criteria += [('date', '<=', end_date)]
            print('\n end_date', end_date)
        move_line_out_ids = self.env['stock.move.line'].search(move_line_out_criteria, order='date asc')
        return move_line_out_ids

    def _get_move_line_out_qty(self, product_id, lot_id, start_date, end_date):
        move_line_out_ids = self._get_move_line_out_ids(
            product_id=product_id,
            lot_id=lot_id,
            start_date=start_date,
            end_date=end_date
        )
        move_line_out_qty = 0
        for move_line_out_id in move_line_out_ids:
            move_line_out_qty += product_id.uom_id._compute_quantity(
                move_line_out_id.quantity, move_line_out_id.product_uom_id)
        return move_line_out_qty

    def _get_move_line_ids(self, product_id, lot_id, start_date, end_date):
        move_line_in_ids = self._get_move_line_in_ids(
            product_id=product_id,
            lot_id=lot_id,
            start_date=start_date,
            end_date=end_date
        )
        move_line_out_ids = self._get_move_line_out_ids(
            product_id=product_id,
            lot_id=lot_id,
            start_date=start_date,
            end_date=end_date
        )
        move_line_ids = move_line_in_ids + move_line_out_ids
        move_line_ids = self.env['stock.move.line'].search([('id', 'in', move_line_ids.ids)], order='date asc')
        return move_line_ids
    
    def get_stock_card_detail_data(self):
        grouped_datas = []
        product_id = self.product_id
        if product_id.tracking != 'none':
            product_lot_ids = self.env['stock.lot'].search([('product_id', '=', product_id.id)])
            lot_ids = self.lot_ids.filtered(lambda l: l.id in product_lot_ids.ids)
            if not lot_ids:
                lot_ids = product_lot_ids
        else:
            lot_ids = [self.env['stock.lot']]
        diff_hours = self._get_diff_hours()
        for lot_id in lot_ids:
            datas = []
            beginning_balance = ending_balance = self._get_beginning_balance(
                product_id=product_id,
                lot_id=lot_id,
            )
            no = 1
            datas.append({
                'no': no,
                'product_name': product_id.display_name,
                'categ_name': product_id.categ_id.name,
                'lot_name': lot_id.display_name or '',
                'trx_date': '',
                'reference': 'Beginning Balance',
                'beginning_qty': beginning_balance,
                'purchase_qty': 0,
                'return_in_qty': 0,
                'adjustment_in_qty': 0,
                'others_in_qty': 0,
                'sale_qty': 0,
                'return_out_qty': 0,
                'adjustment_out_qty': 0,
                'others_out_qty': 0,
                'ending_qty': ending_balance,
            })
            no += 1
            move_line_ids = self._get_move_line_ids(
                product_id=product_id,
                lot_id=lot_id,
                start_date=self.date_start,
                end_date=self.date_end
            )
            location_ids = self.env['stock.location'].search([
                ('id', 'child_of', self.location_id.ids)
            ])
            for move_line_id in move_line_ids:
                beginning_balance = ending_balance
                qty = move_line_id.product_uom_id._compute_quantity(move_line_id.quantity, product_id.uom_id)
                trx_date = ''
                if move_line_id.date:
                    trx_date = move_line_id.date + relativedelta(hours=diff_hours)
                    trx_date = trx_date.strftime('%Y-%m-%d %H:%M:%S')
                purchase_qty = 0
                return_in_qty = 0
                adjustment_in_qty = 0
                others_in_qty = 0
                sale_qty = 0
                return_out_qty = 0
                adjustment_out_qty = 0
                others_out_qty = 0
                if (move_line_id.location_id.id not in location_ids.ids
                        and move_line_id.location_dest_id.id in location_ids.ids):
                    if move_line_id.location_id.usage == 'supplier':
                        purchase_qty = qty
                    elif move_line_id.location_id.usage == 'customer':
                        return_in_qty = qty
                    elif move_line_id.location_id.usage == 'inventory':
                        adjustment_in_qty = qty
                    else:
                        others_in_qty = qty
                elif (move_line_id.location_id.id in location_ids.ids
                      and move_line_id.location_dest_id.id not in location_ids.ids):
                    if move_line_id.location_dest_id.usage == 'customer':
                        sale_qty = qty
                    elif move_line_id.location_dest_id.usage == 'supplier':
                        return_out_qty = qty
                    elif move_line_id.location_dest_id.usage == 'inventory':
                        adjustment_out_qty = qty
                    else:
                        others_in_qty = qty
                ending_balance = (ending_balance + purchase_qty + return_in_qty + adjustment_in_qty +
                                  others_in_qty - sale_qty - return_out_qty - adjustment_out_qty - others_out_qty)
                datas.append({
                    'no': no,
                    'product_name': product_id.display_name,
                    'categ_name': product_id.categ_id.name,
                    'lot_name': lot_id.display_name or '',
                    'trx_date': trx_date,
                    'reference': (move_line_id.picking_id.origin or move_line_id.move_id.origin
                                  or move_line_id.picking_id.name or move_line_id.move_id.name or ''),
                    'beginning_qty': beginning_balance,
                    'purchase_qty': purchase_qty,
                    'return_in_qty': return_in_qty,
                    'adjustment_in_qty': adjustment_in_qty,
                    'others_in_qty': others_in_qty,
                    'sale_qty': sale_qty,
                    'return_out_qty': return_out_qty,
                    'adjustment_out_qty': adjustment_out_qty,
                    'others_out_qty': others_out_qty,
                    'ending_qty': ending_balance,
                })
                no += 1
            beginning_balance = ending_balance
            datas.append({
                'no': no,
                'product_name': product_id.display_name,
                'categ_name': product_id.categ_id.name,
                'lot_name': lot_id.display_name or '',
                'trx_date': '',
                'reference': 'Ending Balance',
                'beginning_qty': beginning_balance,
                'purchase_qty': 0,
                'return_in_qty': 0,
                'adjustment_in_qty': 0,
                'others_in_qty': 0,
                'sale_qty': 0,
                'return_out_qty': 0,
                'adjustment_out_qty': 0,
                'others_out_qty': 0,
                'ending_qty': ending_balance,
            })
            grouped_datas.append(datas)
        return grouped_datas

    def action_export_excel_stock_card_detail(self, wbf, workbook):
        report_name = 'Detalles de la tarjeta de stock'
        worksheet = workbook.add_worksheet(report_name)
        worksheet.merge_range('A2:I3', report_name, wbf['title_doc'])
        columns = [
            ('Nro', 5, 'no', 'no'),
            ('Producto', 50, 'char', 'char'),
            ('Categoría', 40, 'char', 'char'),
            ('Lote / SN', 20, 'char', 'char'),
            ('Fecha', 20, 'char', 'char'),
            ('Referencia', 25, 'char', 'char'),
            ('Comienzo', 20, 'float', 'char'),
            ('Orden de Compra', 20, 'float', 'float'),
            ('Devolución en', 20, 'float', 'float'),
            ('Ajuste de entrada', 20, 'float', 'float'),
            ('Otras entradas', 20, 'float', 'float'),
            ('Orden de Venta', 20, 'float', 'float'),
            ('Regreso', 20, 'float', 'float'),
            ('Ajuste de salida', 20, 'float', 'float'),
            ('Otras salidas', 20, 'float', 'float'),
            ('Final', 20, 'float', 'char'),
        ]
        row = 4
        first_row = end_row = 0
        grouped_datas = self.get_stock_card_detail_data()

        for datas in grouped_datas:
            col = 0
            for column in columns:
                column_name = column[0]
                column_width = column[1]
                worksheet.set_column(col, col, column_width)
                col_alphabet = xlsxwriter.utility.xl_col_to_name(col)
                worksheet.write(f'{col_alphabet}{row}', column_name, wbf['header_orange'])

                col += 1
            row += 1

            first_row = end_row = row
            for data in datas:
                worksheet.write(f'A{row}', data['no'], wbf['content'])
                worksheet.write(f'B{row}', data['product_name'], wbf['content'])
                worksheet.write(f'C{row}', data['categ_name'], wbf['content'])
                worksheet.write(f'D{row}', data['lot_name'], wbf['content'])
                worksheet.write(f'E{row}', data['trx_date'], wbf['content'])
                worksheet.write(f'F{row}', data['reference'], wbf['content'])
                worksheet.write(f'G{row}', data['beginning_qty'], wbf['content_float'])
                worksheet.write(f'H{row}', data['purchase_qty'], wbf['content_float'])
                worksheet.write(f'I{row}', data['return_in_qty'], wbf['content_float'])
                worksheet.write(f'J{row}', data['adjustment_in_qty'], wbf['content_float'])
                worksheet.write(f'K{row}', data['others_in_qty'], wbf['content_float'])
                worksheet.write(f'L{row}', data['sale_qty'], wbf['content_float'])
                worksheet.write(f'M{row}', data['return_out_qty'], wbf['content_float'])
                worksheet.write(f'N{row}', data['adjustment_out_qty'], wbf['content_float'])
                worksheet.write(f'O{row}', data['others_out_qty'], wbf['content_float'])
                worksheet.write(f'P{row}', data['ending_qty'], wbf['content_float'])
                end_row = row
                row += 1
            worksheet.merge_range('A%s:B%s' % (row, row), 'Grand Total', wbf['total_orange'])
            current_index = 0
            col = -1
            for column in columns:
                current_index += 1
                col += 1
                if current_index <= 2:
                    continue
                total_type = column[3]
                col_alphabet = xlsxwriter.utility.xl_col_to_name(col)
                if total_type in ['float', 'number']:
                    col_value = '{=SUM(%s%s:%s%s)}' % (col_alphabet, first_row, col_alphabet, end_row)
                    if total_type == 'float':
                        wbf_total = wbf['total_float_orange']
                    else:
                        wbf_total = wbf['total_number_orange']
                else:
                    col_value = ''
                    wbf_total = wbf['header_orange']

                worksheet.write(f'{col_alphabet}{row}', col_value, wbf_total)
            row += 3
        # tidak perlu total otomatis
        columns = []
        return wbf, workbook, worksheet, report_name, columns, row, first_row, end_row
