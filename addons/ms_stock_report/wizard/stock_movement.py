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

    def get_stock_movement_data(self):
        datas = []
        move_line_in_criteria = [
            ('state', '=', 'done'),
        ]
        diff_hours = self._get_diff_hours()
        start_date = self.date_start
        end_date = self.date_end
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
        if self.product_ids:
            move_line_in_criteria += [('product_id', 'in', self.product_ids.ids)]
        if self.location_ids:
            move_line_in_criteria += [
                '|',
                ('location_id', 'child_of', self.location_ids.ids),
                ('location_dest_id', 'child_of', self.location_ids.ids),
            ]
        if self.lot_ids:
            move_line_in_criteria += [('lot_id', 'in', self.lot_ids.ids)]
        move_line_ids = self.env['stock.move.line'].search(move_line_in_criteria, order='date asc')
        no = 1
        for move_line_id in move_line_ids:
            transfer_date = ''
            if move_line_id.date:
                transfer_date = move_line_id.date + relativedelta(hours=diff_hours)
                transfer_date = transfer_date.strftime('%Y-%m-%d %H:%M:%S')
            qty = move_line_id.product_uom_id._compute_quantity(move_line_id.quantity, move_line_id.product_id.uom_id)
            datas.append({
                'no': no,
                'product_name': move_line_id.product_id.display_name,
                'categ_name': move_line_id.product_id.categ_id.name,
                'lot_name': move_line_id.lot_id.display_name or '',
                'location_name': move_line_id.location_id.display_name,
                'dest_location_name': move_line_id.location_dest_id.display_name,
                'reference': (move_line_id.picking_id.origin or move_line_id.move_id.origin or move_line_id.picking_id.name
                              or move_line_id.move_id.name or ''),
                'transfer_date': transfer_date,
                'qty': qty,
            })
            no += 1
        return datas

    def action_export_excel_stock_movement(self, wbf, workbook):
        report_name = 'Movimiento de acciones'
        worksheet = workbook.add_worksheet(report_name)
        worksheet.merge_range('A2:I3', report_name, wbf['title_doc'])
        columns = [
            ('Nro', 5, 'no', 'no'),
            ('Producto', 50, 'char', 'char'),
            ('Categoría', 40, 'char', 'char'),
            ('Lote / SN', 20, 'char', 'char'),
            ('Ubicación de origen', 40, 'char', 'char'),
            ('Ubicación de destino', 40, 'char', 'char'),
            ('Referencia', 25, 'char', 'char'),
            ('Fecha de transferencia', 20, 'char', 'char'),
            ('Cantidad', 20, 'float', 'float'),
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

        first_row = end_row = row

        datas = self.get_stock_movement_data()

        for data in datas:
            worksheet.write(f'A{row}', data['no'], wbf['content'])
            worksheet.write(f'B{row}', data['product_name'], wbf['content'])
            worksheet.write(f'C{row}', data['categ_name'], wbf['content'])
            worksheet.write(f'D{row}', data['lot_name'], wbf['content'])
            worksheet.write(f'E{row}', data['location_name'], wbf['content'])
            worksheet.write(f'F{row}', data['dest_location_name'], wbf['content'])
            worksheet.write(f'G{row}', data['reference'], wbf['content'])
            worksheet.write(f'H{row}', data['transfer_date'], wbf['content'])
            worksheet.write(f'I{row}', data['qty'], wbf['content_float'])
            end_row = row
            row += 1
        return wbf, workbook, worksheet, report_name, columns, row, first_row, end_row
