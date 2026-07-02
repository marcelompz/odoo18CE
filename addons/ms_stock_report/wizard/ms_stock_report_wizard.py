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
    _name = "ms.stock.report.wizard"
    _description = "All In One Stock Reports"

    @api.model
    def get_default_date_tz(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz or 'UTC'))

    name = fields.Char(
        string="Name",
        default='All In One Stock Reports',
        required=False)
    type = fields.Selection(
        string='Type',
        selection=[
            ('current_stock', 'Current Stock'),
            ('stock_card_detail', 'Stock Card Detail'),
            ('stock_card_summary', 'Stock Card Summary'),
            ('stock_movement', 'Stock Movement'),
        ], required=True)
    date_start = fields.Date(
        string='Date Start',
        required=False)
    date_end = fields.Date(
        string='Date End',
        required=False)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=False)
    product_tracking = fields.Selection(related='product_id.tracking')
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        required=False)
    product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products',
        required=False)
    lot_ids = fields.Many2many(
        comodel_name='stock.lot',
        string='Lots / Serial Numbers',
        required=False)
    location_ids = fields.Many2many(
        comodel_name='stock.location',
        string='Locations',
        required=False)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.onchange('product_id')
    def onchange_product(self):
        self.lot_ids = False

    @api.constrains('date_end', 'type')
    def _check_date_end_for_current_stock(self):
        for record in self:
            if record.type == 'current_stock' and record.date_end and record.date_end > fields.Date.today():
                raise ValidationError(_("For 'Current Stock', the 'Date End' cannot be in the future."))
            if record.type == 'current_stock' and not record.date_end:
                 record.date_end = fields.Date.today()

    def _get_diff_hours(self):
        datetime_format = '%Y-%m-%d %H:%M:%S'
        utc = datetime.now().strftime(datetime_format)
        utc = datetime.strptime(utc, datetime_format)
        tz = self.get_default_date_tz().strftime(datetime_format)
        tz = datetime.strptime(tz, datetime_format)
        duration = tz - utc
        diff_hours = duration.seconds / 60 / 60
        return diff_hours

    def action_view(self):
        base_url = self.env.user.get_base_url()
        url = f'{base_url}/{self.type}/{self.id}'
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_export_excel(self):
        datetime_string = self.get_default_date_tz().strftime("%Y-%m-%d %H:%M:%S")
        date_string = self.get_default_date_tz().strftime("%Y-%m-%d")

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        wbf, workbook = self.add_workbook_format(workbook)

        wbf, workbook, worksheet, report_name, columns, row, first_row, end_row = getattr(
            self, f'action_export_excel_{self.type}')(
                wbf=wbf,
                workbook=workbook,
            )

        filename = '%s %s' % (report_name, date_string)

        if columns:
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

        worksheet.write('A%s' % (row + 2), 'Date %s (%s)' % (
            datetime_string, self.env.user.tz or 'UTC'), wbf['content_datetime'])
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out, 'datas_fname': filename})
        fp.close()
        filename += '%2Exlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=datas&download=true&filename=' + filename,
        }

    def action_export_pdf(self):
        return self.env.ref(f'ms_stock_report.report_{self.type}').report_action(self)

    def add_workbook_format(self, workbook):
        colors = {
            'white_orange': '#FFFFDB',
            'orange': '#FFC300',
            'red': '#FF0000',
            'yellow': '#F6FA03',
        }

        wbf = {}
        wbf['header'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': '#FFFFDB', 'font_color': '#000000', 'font_name': 'Georgia'})
        wbf['header'].set_border()

        wbf['header_orange'] = workbook.add_format({
            'bold': 1, 'align': 'center', 'bg_color': colors['orange'], 'font_color': '#000000',
            'font_name': 'Georgia'})
        wbf['header_orange'].set_border()

        wbf['header_yellow'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': colors['yellow'],
             'font_color': '#000000', 'font_name': 'Georgia'})
        wbf['header_yellow'].set_border()

        wbf['header_no'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': '#FFFFDB', 'font_color': '#000000', 'font_name': 'Georgia'})
        wbf['header_no'].set_border()
        wbf['header_no'].set_align('vcenter')

        wbf['footer'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})

        wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'font_name': 'Georgia'})
        wbf['content_datetime'].set_left()
        wbf['content_datetime'].set_right()

        wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd', 'font_name': 'Georgia'})
        wbf['content_date'].set_left()
        wbf['content_date'].set_right()

        wbf['title_doc'] = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 20,
            'font_name': 'Georgia',
        })

        wbf['company'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})
        wbf['company'].set_font_size(11)

        wbf['content'] = workbook.add_format()
        wbf['content'].set_left()
        wbf['content'].set_right()

        wbf['content_float'] = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'font_name': 'Georgia'})
        wbf['content_float'].set_right()
        wbf['content_float'].set_left()

        wbf['content_number'] = workbook.add_format({'align': 'right', 'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['content_number'].set_right()
        wbf['content_number'].set_left()

        wbf['content_percent'] = workbook.add_format({'align': 'right', 'num_format': '0.00%', 'font_name': 'Georgia'})
        wbf['content_percent'].set_right()
        wbf['content_percent'].set_left()

        wbf['total_float'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['white_orange'], 'align': 'right',
             'num_format': '#,##0.00', 'font_name': 'Georgia'})
        wbf['total_float'].set_top()
        wbf['total_float'].set_bottom()
        wbf['total_float'].set_left()
        wbf['total_float'].set_right()

        wbf['total_number'] = workbook.add_format(
            {'align': 'right', 'bg_color': colors['white_orange'], 'bold': 1,
             'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['total_number'].set_top()
        wbf['total_number'].set_bottom()
        wbf['total_number'].set_left()
        wbf['total_number'].set_right()

        wbf['total'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['white_orange'],
             'align': 'center', 'font_name': 'Georgia'})
        wbf['total'].set_left()
        wbf['total'].set_right()
        wbf['total'].set_top()
        wbf['total'].set_bottom()

        wbf['total_float_yellow'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['yellow'], 'align': 'right',
             'num_format': '#,##0.00', 'font_name': 'Georgia'})
        wbf['total_float_yellow'].set_top()
        wbf['total_float_yellow'].set_bottom()
        wbf['total_float_yellow'].set_left()
        wbf['total_float_yellow'].set_right()

        wbf['total_number_yellow'] = workbook.add_format(
            {'align': 'right', 'bg_color': colors['yellow'], 'bold': 1, 'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['total_number_yellow'].set_top()
        wbf['total_number_yellow'].set_bottom()
        wbf['total_number_yellow'].set_left()
        wbf['total_number_yellow'].set_right()

        wbf['total_yellow'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['yellow'], 'align': 'center', 'font_name': 'Georgia'})
        wbf['total_yellow'].set_left()
        wbf['total_yellow'].set_right()
        wbf['total_yellow'].set_top()
        wbf['total_yellow'].set_bottom()

        wbf['total_float_orange'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['orange'], 'align': 'right',
             'num_format': '#,##0.00', 'font_name': 'Georgia'})
        wbf['total_float_orange'].set_top()
        wbf['total_float_orange'].set_bottom()
        wbf['total_float_orange'].set_left()
        wbf['total_float_orange'].set_right()

        wbf['total_number_orange'] = workbook.add_format(
            {'align': 'right', 'bg_color': colors['orange'], 'bold': 1, 'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['total_number_orange'].set_top()
        wbf['total_number_orange'].set_bottom()
        wbf['total_number_orange'].set_left()
        wbf['total_number_orange'].set_right()

        wbf['total_orange'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['orange'], 'align': 'center', 'font_name': 'Georgia'})
        wbf['total_orange'].set_left()
        wbf['total_orange'].set_right()
        wbf['total_orange'].set_top()
        wbf['total_orange'].set_bottom()

        wbf['header_detail_space'] = workbook.add_format({'font_name': 'Georgia'})
        wbf['header_detail_space'].set_left()
        wbf['header_detail_space'].set_right()
        wbf['header_detail_space'].set_top()
        wbf['header_detail_space'].set_bottom()

        wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2', 'font_name': 'Georgia'})
        wbf['header_detail'].set_left()
        wbf['header_detail'].set_right()
        wbf['header_detail'].set_top()
        wbf['header_detail'].set_bottom()

        return wbf, workbook
