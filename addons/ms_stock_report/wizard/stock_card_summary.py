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

    def get_stock_card_summary_data(self):
        datas = []
        product_ids = self.product_ids
        if not product_ids:
            product_ids = self.env['product.product'].search([])
        no = 1
        location_ids = self.env['stock.location'].search([
            ('id', 'child_of', self.location_id.ids)
        ])
        for product_id in product_ids:
            if product_id.tracking != 'none':
                product_lot_ids = self.env['stock.lot'].search([('product_id', '=', product_id.id)])
                lot_ids = self.lot_ids.filtered(lambda l: l.id in product_lot_ids.ids)
                if not lot_ids:
                    lot_ids = product_lot_ids
            else:
                lot_ids = [self.env['stock.lot']]
            for lot_id in lot_ids:
                beginning_balance = self._get_beginning_balance(
                    product_id=product_id,
                    lot_id=lot_id,
                )
                move_line_ids = self._get_move_line_ids(
                    product_id=product_id,
                    lot_id=lot_id,
                    start_date=self.date_start,
                    end_date=self.date_end
                )
                purchase_qty = 0
                return_in_qty = 0
                adjustment_in_qty = 0
                others_in_qty = 0
                sale_qty = 0
                return_out_qty = 0
                adjustment_out_qty = 0
                others_out_qty = 0
                for move_line_id in move_line_ids:
                    qty = move_line_id.product_uom_id._compute_quantity(move_line_id.quantity, product_id.uom_id)
                    if (move_line_id.location_id.id not in location_ids.ids
                            and move_line_id.location_dest_id.id in location_ids.ids):
                        if move_line_id.location_id.usage == 'supplier':
                            purchase_qty += qty
                        elif move_line_id.location_id.usage == 'customer':
                            return_in_qty += qty
                        elif move_line_id.location_id.usage == 'inventory':
                            adjustment_in_qty += qty
                        else:
                            others_in_qty += qty
                    elif (move_line_id.location_id.id in location_ids.ids
                          and move_line_id.location_dest_id.id not in location_ids.ids):
                        if move_line_id.location_dest_id.usage == 'customer':
                            sale_qty += qty
                        elif move_line_id.location_dest_id.usage == 'supplier':
                            return_out_qty += qty
                        elif move_line_id.location_dest_id.usage == 'inventory':
                            adjustment_out_qty += qty
                        else:
                            others_in_qty += qty
                ending_balance = (beginning_balance + purchase_qty + return_in_qty + adjustment_in_qty +
                                  others_in_qty - sale_qty - return_out_qty - adjustment_out_qty - others_out_qty)
                datas.append({
                    'no': no,
                    'product_name': product_id.display_name,
                    'categ_name': product_id.categ_id.name,
                    'lot_name': lot_id.display_name or '',
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
        return datas

    def action_export_excel_stock_card_summary(self, wbf, workbook):
        report_name = 'Resumen de la tarjeta de stock'
        worksheet = workbook.add_worksheet(report_name)
        worksheet.merge_range('A2:I3', report_name, wbf['title_doc'])
        columns = [
            ('Nro', 5, 'no', 'no'),
            ('Producto', 50, 'char', 'char'),
            ('Categoría', 40, 'char', 'char'),
            ('Lote / SN', 20, 'char', 'char'),
            ('Comienzo', 20, 'float', 'float'),
            ('Orden de Compra', 20, 'float', 'float'),
            ('Devolución en', 20, 'float', 'float'),
            ('Ajuste de entrada', 20, 'float', 'float'),
            ('Otras entradas', 20, 'float', 'float'),
            ('Orden de Venta', 20, 'float', 'float'),
            ('Regreso', 20, 'float', 'float'),
            ('Ajuste de salida', 20, 'float', 'float'),
            ('Otras salidas', 20, 'float', 'float'),
            ('Final', 20, 'float', 'float'),
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

        datas = self.get_stock_card_summary_data()
        for data in datas:
            worksheet.write(f'A{row}', data['no'], wbf['content'])
            worksheet.write(f'B{row}', data['product_name'], wbf['content'])
            worksheet.write(f'C{row}', data['categ_name'], wbf['content'])
            worksheet.write(f'D{row}', data['lot_name'], wbf['content'])
            worksheet.write(f'E{row}', data['beginning_qty'], wbf['content_float'])
            worksheet.write(f'F{row}', data['purchase_qty'], wbf['content_float'])
            worksheet.write(f'G{row}', data['return_in_qty'], wbf['content_float'])
            worksheet.write(f'H{row}', data['adjustment_in_qty'], wbf['content_float'])
            worksheet.write(f'I{row}', data['others_in_qty'], wbf['content_float'])
            worksheet.write(f'J{row}', data['sale_qty'], wbf['content_float'])
            worksheet.write(f'K{row}', data['return_out_qty'], wbf['content_float'])
            worksheet.write(f'L{row}', data['adjustment_out_qty'], wbf['content_float'])
            worksheet.write(f'M{row}', data['others_out_qty'], wbf['content_float'])
            worksheet.write(f'N{row}', data['ending_qty'], wbf['content_float'])
            end_row = row
            row += 1
        return wbf, workbook, worksheet, report_name, columns, row, first_row, end_row
