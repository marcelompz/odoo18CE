# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import io
import xlsxwriter


class ReporteCompraventaController(http.Controller):

    @http.route('/reporte_compraventa/compras/xlsx/<int:wizard_id>', type='http', auth='user')
    def export_compras_xlsx(self, wizard_id, **kwargs):
        """Exportar reporte de compras a Excel"""
        wizard = request.env['reporte_compraventa.wizardcompra'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()

        # Crear archivo Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Generar reporte usando el modelo existente
        report_model = request.env['report.reporte_compraventa.reporte_compra_xlsx']
        
        # Generar el Excel usando el método existente - pasando el wizard como datas
        report_model.generate_xlsx_report(workbook, None, wizard)
        
        workbook.close()
        output.seek(0)
        
        # Preparar respuesta HTTP
        filename = f'Libro_Compras_{wizard.fecha_inicio}_{wizard.fecha_fin}.xlsx'
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )
        
        return response

    @http.route('/reporte_compraventa/ventas/xlsx/<int:wizard_id>', type='http', auth='user')
    def export_ventas_xlsx(self, wizard_id, **kwargs):
        """Exportar reporte de ventas a Excel"""
        wizard = request.env['reporte_compraventa.wizardventa'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()

        # Crear archivo Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Generar reporte usando el modelo existente
        report_model = request.env['report.reporte_compraventa.reporte_venta_xlsx']
        
        # Generar el Excel usando el método existente - pasando el wizard como datas
        report_model.generate_xlsx_report(workbook, None, wizard)
        
        workbook.close()
        output.seek(0)
        
        # Preparar respuesta HTTP
        filename = f'Libro_Ventas_{wizard.fecha_inicio}_{wizard.fecha_fin}.xlsx'
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )
        
        return response
