# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import io
import xlsxwriter
from odoo import fields, models
from odoo.tools import json_default
import json
from datetime import datetime, timedelta, time

from odoo.exceptions import UserError


class TurnoverReport(models.TransientModel):
    """Wizard created for to select date, products, categories, companies and
    warehouses. The records are filtered by using this fields"""
    _name = "turnover.report"
    _description = "Turnover Report"

    start_date = fields.Date(string="Start Date",
                             help="Select inventory start date.", default=lambda self: fields.Date.context_today(self))
    end_date = fields.Date(string="End Date",
                           help="Select inventory end date.", default=lambda self: fields.Date.context_today(self))
    product_ids = fields.Many2many('product.product', string="Products",
                                   default=lambda self: self.env[
                                       'product.product'].search([], limit=1),
                                   help="Select multiple products "
                                        "from the list.")
    category_ids = fields.Many2many('product.category', string="Category",
                                    default=lambda self: self._default_categ_ids(),
                                    help="Select multiple categories "
                                         "from the list")
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse",
                                     default=lambda self: self._default_warehouse_ids(),
                                     help="Select multiple warehouses "
                                          "from the list.")
    company_ids = fields.Many2many('res.company', string="Company",
                                   default=lambda self: self.env.company,
                                   help="Select multiple companies "
                                        "from the list.")
    only_purchase_sales = fields.Boolean(
                                    string="Solo Compras y Ventas",
                                    help="Si se marca, no se incluirán transferencias internas ni ajustes manuales.",
                                    default=False)

    def _default_categ_ids(self):
        """Return default category to selection field."""
        category = self.env['product.product'].search(
            [], limit=1).product_tmpl_id.categ_id
        return [(6, 0, [category.id])] if category else []

    def _default_warehouse_ids(self):
        """Return default warehouse to selection field."""
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        return [(6, 0, [warehouse.id])] if warehouse else []

    def get_xlsx_report(self, data, response):
        """This function is for create xlsx report"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Informe de análisis de rotación de inventario')
        head = workbook.add_format({'align': 'center', 'bold': True,
                                    'font_size': '30px'})
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 50)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)
        sheet.merge_range('A3:G1', 'Informe de análisis de rotación de inventario', head)
        row = 6
        column = 0
        if data['start_date']:
            sheet.write(5, 1, 'Fecha inicio:', workbook.add_format({
                'align': 'center', 'bold': True}))
            sheet.write(5, 2, data['start_date'], workbook.add_format({
                'align': 'center', 'bold': True}))
            row += 1
        if data['end_date']:
            sheet.write(5, 3, 'Fecha final:', workbook.add_format({
                'align': 'center', 'bold': True}))
            sheet.write(5, 4, data['end_date'], workbook.add_format({
                'align': 'center', 'bold': True}))
            row += 1
        head_table = workbook.add_format({'align': 'center', 'bold': True})
        sheet.write(row, column, 'Ref.Interna', workbook.add_format({'align': 'left', 'bold': True}))
        column += 1
        sheet.write(row, column, 'Producto', workbook.add_format({'align': 'left', 'bold': True}))
        column += 1
        sheet.write(row, column, 'Categoría', head_table)
        column += 1
        sheet.write(row, column, 'Stock inicial', head_table)
        # column += 1
        # sheet.write(row, column, 'Turnover Ratio', head_table)
        # column += 1
        # sheet.write(row, column, 'Average Stock', head_table)
        column += 1
        sheet.write(row, column, 'Entrada', head_table)
        column += 1
        sheet.write(row, column, 'Salida', head_table)
        column += 1
        sheet.write(row, column, 'Stock final', head_table)
        for datas in data['stock_report']:
            row += 1
            column = 0
            table_body = workbook.add_format({'align': 'center'})
            sheet.write(row, column, datas['default_code'], workbook.add_format({'align': 'left'}))
            column += 1
            sheet.write(row, column, datas['product_name'], workbook.add_format({'align': 'left'}))
            column += 1
            sheet.write(row, column, datas['category'], workbook.add_format({'align': 'left'}))
            column += 1
            sheet.write(row, column, datas['opening_stock'], table_body)
            # column += 1
            # sheet.write(row, column, datas['turnover_ratio'], table_body)
            # column += 1
            # sheet.write(row, column, datas['average_stock'], table_body)
            column += 1
            sheet.write(row, column, datas['purchase_count'], table_body)
            column += 1
            sheet.write(row, column, datas['sale_count'], table_body)
            column += 1
            sheet.write(row, column, datas['closing_stock'], table_body)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def _get_turnover_data(self):
        # 1. Obtener productos
        product_domain = [('type', '=', 'consu')] # Cambiar a 'product' si usas almacenables en v18
        if self.product_ids:
            product_domain.append(('id', 'in', self.product_ids.ids))
        if self.category_ids:
            product_domain.append(('categ_id', 'child_of', self.category_ids.ids))
        products = self.env['product.product'].search(product_domain)
        if not products: return []

        # 2. Obtener ubicaciones internas seleccionadas
        locations_to_analyze = self.env['stock.location'].sudo()
        if self.warehouse_ids:
            locations_to_analyze = locations_to_analyze.search([('id', 'child_of', self.warehouse_ids.view_location_id.ids), ('usage', '=', 'internal')])
        elif self.company_ids:
            locations_to_analyze = locations_to_analyze.search([('company_id', 'in', self.company_ids.ids), ('usage', '=', 'internal')])
        else: return []

        if not locations_to_analyze: return []
        location_ids = locations_to_analyze.ids
        
        # 3. Preparar el dominio de movimientos
        domain = [
            ('product_id', 'in', products.ids),
            ('state', '=', 'done'),
            '|',
                ('location_id', 'in', location_ids),
                ('location_dest_id', 'in', location_ids),
        ]

        # --- LÓGICA DE FILTRADO PARA COMPRAS Y VENTAS ---
        if self.only_purchase_sales:
            # Entrada de Proveedor (Compra) O Salida a Cliente (Venta)
            domain += [
                '|',
                '&', ('location_id.usage', '=', 'supplier'), ('location_dest_id.id', 'in', location_ids),
                '&', ('location_id.id', 'in', location_ids), ('location_dest_id.usage', '=', 'customer')
            ]

        fields_to_group_by = ['product_id', 'location_id', 'location_dest_id', 'date:day']
        fields_to_aggregate = ['quantity:sum']

        all_moves_data = self.env['stock.move.line'].sudo()._read_group(
            domain,
            fields_to_group_by,
            fields_to_aggregate
        )
        
        # 4. Procesar los resultados
        stock_report_dict = {}
        for p in products:
            stock_report_dict[p.id] = {
                'id': p.id, 'default_code': p.default_code or '', 'product': p.display_name,
                'opening_stock': 0.0, 'purchase_count': 0.0, 'sale_count': 0.0,
                'product_name': p.name, 'category': p.categ_id.name,
            }

        start_date_val = self.start_date
        end_date_val = self.end_date

        for product_rec, location_rec, dest_rec, date_val_dt, qty_sum in all_moves_data:
            product_id = product_rec.id
            date_val = date_val_dt.date()
            
            # Identificar si es entrada o salida respecto a nuestras ubicaciones internas
            is_in = dest_rec.id in location_ids and location_rec.id not in location_ids
            is_out = location_rec.id in location_ids and dest_rec.id not in location_ids

            if date_val < start_date_val:
                if is_in: stock_report_dict[product_id]['opening_stock'] += qty_sum
                elif is_out: stock_report_dict[product_id]['opening_stock'] -= qty_sum
            elif start_date_val <= date_val <= end_date_val:
                if is_in: stock_report_dict[product_id]['purchase_count'] += qty_sum
                elif is_out: stock_report_dict[product_id]['sale_count'] += qty_sum
        
        # 5. Calcular Totales Finales
        stock_report = list(stock_report_dict.values())
        for data in stock_report:
            data['closing_stock'] = data['opening_stock'] + data['purchase_count'] - data['sale_count']
            # Evitar errores en ratios
            avg = (data['opening_stock'] + data['closing_stock']) / 2
            data['average_stock'] = round(avg, 2)
            data['turnover_ratio'] = round(data['sale_count'] / avg, 2) if avg > 0 else 0.0
            
        return stock_report

    def action_pdf_report_generate(self):
        data = {
            'stock_report': self._get_turnover_data(),
            'start_date': self.start_date.strftime('%d/%m/%Y'),
            'end_date': self.end_date.strftime('%d/%m/%Y'),
        }
        return self.env.ref('inventory_turnover_report_analysis.inventory_turnover_report').report_action(self, data=data)

    def action_xlsx_report_generate(self):
        data = {
            'stock_report': self._get_turnover_data(),
            'start_date': self.start_date.strftime('%d/%m/%Y'),
            'end_date': self.end_date.strftime('%d/%m/%Y'),
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'turnover.report',
                     'options': json.dumps(data, default=json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Informe de análisis de rotación de inventario',
                     },
            'report_type': 'xlsx',
        }   

    def action_data_fetch(self):
        """
        Genera y muestra los datos de rotación en una vista de lista.
        Usa el nuevo método de obtención de datos.
        """
        # 1. Obtenemos los datos con el nuevo método centralizado
        filtered_records = self._get_turnover_data()

        # 2. Preparamos los valores para la creación en lote (más eficiente)
        fetch_data_model = self.env['fetch.data']
        fetch_data_model.search([]).unlink() # Limpiamos los registros antiguos
        
        vals_list = []
        for rec in filtered_records:
            vals_list.append({
                'company_id': rec['company_id'],
                'warehouse_id': rec['warehouse_id'],
                'product_id': rec['id'],
                'category_id': rec['category_id'],
                'opening_stock': rec['opening_stock'],
                'closing_stock': rec['closing_stock'],
                'average_stock': rec['average_stock'],
                'sale_count': rec['sale_count'],
                'purchase_count': rec['purchase_count'],
                'turnover_ratio': rec['turnover_ratio'],
            })
        
        if vals_list:
            fetch_data_model.create(vals_list)

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'fetch.data',
            'name': 'Informe de análisis de rotación',
            'target': 'current',
            'context': {"create": False},
        }

    def action_generate_graph_view(self):
        """
        Genera y muestra los datos de rotación en una vista de gráfico.
        Usa el nuevo método de obtención de datos.
        """
        # 1. Obtenemos los datos con el nuevo método centralizado
        filtered_records = self._get_turnover_data()
        
        # 2. Preparamos los valores para la creación en lote
        graph_model = self.env['turnover.graph.analysis']
        graph_model.search([]).unlink() # Limpiamos los registros antiguos
        
        vals_list = []
        for rec in filtered_records:
            vals_list.append({
                'company_id': rec['company_id'],
                'warehouse_id': rec['warehouse_id'],
                'product_id': rec['id'],
                'category_id': rec['category_id'],
                'opening_stock': rec['opening_stock'],
                'closing_stock': rec['closing_stock'],
                'average_stock': rec['average_stock'],
                'sale_count': rec['sale_count'],
                'purchase_count': rec['purchase_count'],
                'turnover_ratio': rec['turnover_ratio'],
            })
        
        if vals_list:
            graph_model.create(vals_list)

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'graph', # Añadir 'form' es una buena práctica
            'res_model': 'turnover.graph.analysis',
            'name': 'Análisis de rotación',
            'target': 'current',
            'context': {"create": False},
        }
