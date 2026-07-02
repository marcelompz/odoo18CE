# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import base64
import io

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None


class HrPayrollIPSExportWizard(models.TransientModel):
    _name = 'hr.payroll.ips.export.wizard'
    _description = 'Exportación Planilla IPS a Excel'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lote de nómina', required=False)
    file_data = fields.Binary(string='Archivo', readonly=True)
    filename = fields.Char(readonly=True)

    def action_generate_file(self):
        self.ensure_one()
        if not self.payslip_run_id:
            raise UserError(_("Selecciona un lote de nómina."))
        if xlsxwriter is None:
            raise UserError(_("El módulo python 'xlsxwriter' no está instalado. Instálalo en el servidor para generar la planilla."))

        payslips = self.payslip_run_id.slip_ids.filtered(lambda s: s.state in ('done', 'paid'))
        if not payslips:
            raise UserError(_("El lote no tiene recibos en estado 'Hecho' o 'Pagado'."))

        # Ordenar por nombre del empleado
        payslips = payslips.sorted(lambda p: p.employee_id.name or '')

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Planilla IPS')

        # Definir columnas según requerimiento
        headers = [
            'Ide Asecot',
            'Nro Cic',
            'Asegurado',
            'Salario Real',
            'Dias',
            'Salario Imponible',
            'Mov',
        ]
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Escribir encabezados
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 15)  # Ancho de columna

        # Formato para números
        number_format = workbook.add_format({'num_format': '#,##0', 'align': 'right'})
        number_format_int = workbook.add_format({'num_format': '0', 'align': 'right'})
        text_format = workbook.add_format({'align': 'left'})
        text_center_format = workbook.add_format({'align': 'center'})

        # Escribir datos
        for row, slip in enumerate(payslips, start=1):
            employee = slip.employee_id
            
            # Ide Asecot (Número de asegurado IPS)
            ide_asecot = employee.ips_number or ''
            worksheet.write(row, 0, ide_asecot, text_format)
            
            # Nro Cic (Número de CI)
            nro_cic = employee.identification_id or ''
            worksheet.write(row, 1, nro_cic, text_format)
            
            # Asegurado (Nombre del empleado)
            asegurado = employee.name or ''
            worksheet.write(row, 2, asegurado, text_format)
            
            # Salario Real (Salario bruto/total de ingresos)
            salario_real = slip.get_total_ingresos() or 0.0
            worksheet.write_number(row, 3, salario_real, number_format)
            
            # Dias (Días trabajados)
            dias_trabajados = slip.get_worked_days() or 0
            worksheet.write_number(row, 4, dias_trabajados, number_format_int)
            
            # Salario Imponible (Salario sobre el cual se calcula IPS - mismo que salario real)
            salario_imponible = slip.get_total_ingresos() or 0.0
            worksheet.write_number(row, 5, salario_imponible, number_format)
            
            # Mov (30 días = "normal", menos de 30 = "VARIAS CAUSAS")
            if dias_trabajados >= 30:
                mov = 'normal'
            else:
                mov = 'VARIAS CAUSAS'
            worksheet.write(row, 6, mov, text_center_format)

        workbook.close()
        output.seek(0)
        filename = 'Planilla_IPS_%s.xlsx' % (self.payslip_run_id.name or 'lote')
        file_data = base64.b64encode(output.read())
        
        # Actualizar el wizard con el archivo generado
        self.write({
            'file_data': file_data,
            'filename': filename,
        })
        
        # Crear un attachment para descargar el archivo
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_data,
            'res_model': 'hr.payroll.ips.export.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        # Retornar acción de descarga del attachment
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

