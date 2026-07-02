# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _
from datetime import datetime, date
import xlsxwriter
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class Resolucion77ExportWizard(models.TransientModel):
    _name = 'resolucion.77.export.wizard'
    _description = 'Wizard de Exportación Resolución 77'

    name = fields.Char(string="Nombre del Reporte", default="Cuadro de Depreciación")
    
    # Filtros de fecha
    fecha_desde = fields.Date(string="Fecha Adquisición Desde",
                             help="Filtrar bienes adquiridos desde esta fecha")
    fecha_hasta = fields.Date(string="Fecha Adquisición Hasta",
                             help="Filtrar bienes adquiridos hasta esta fecha")
    
    # Filtros de estado
    incluir_activos = fields.Boolean(string="Incluir Bienes Activos", default=True)
    incluir_dados_baja = fields.Boolean(string="Incluir Bienes Dados de Baja", default=False)
    solo_incluir_en_reporte = fields.Boolean(string="Solo Marcados para Reporte", default=True)
    
    # Filtros de categoría
    categoria_ids = fields.Many2many('resolucion.77.category.template', 
                                    string="Filtrar por Categorías",
                                    help="Dejar vacío para incluir todas las categorías")
    
    # Configuración del reporte
    ejercicio_fiscal = fields.Integer(string="Ejercicio Fiscal", 
                                     default=lambda self: date.today().year,
                                     required=True)
    fecha_cierre_fiscal = fields.Date(string="Fecha de Cierre Fiscal",
                                     default=lambda self: date(date.today().year, 12, 31),
                                     required=True)
    
    # Configuración de formato
    incluir_totales = fields.Boolean(string="Incluir Totales", default=True)
    incluir_encabezado_empresa = fields.Boolean(string="Incluir Datos de Empresa", default=True)
    incluir_fecha_generacion = fields.Boolean(string="Incluir Fecha de Generación", default=True)
    
    # Configuración de moneda
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                 default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Compañía', 
                                default=lambda self: self.env.company)

    @api.model
    def default_get(self, fields_list):
        """Override default_get to ensure proper initialization"""
        try:
            res = super().default_get(fields_list)
            # Asegurar que los valores por defecto están bien establecidos
            if 'company_id' not in res or not res.get('company_id'):
                res['company_id'] = self.env.company.id
            if 'currency_id' not in res or not res.get('currency_id'):
                res['currency_id'] = self.env.company.currency_id.id
            return res
        except Exception as e:
            _logger.error(f"Error in default_get for export wizard: {str(e)}")
            # Retornar valores mínimos seguros
            return {
                'company_id': self.env.company.id,
                'currency_id': self.env.company.currency_id.id,
                'ejercicio_fiscal': date.today().year,
                'fecha_cierre_fiscal': date(date.today().year, 12, 31),
            }

    def action_export_excel(self):
        """Acción para exportar a Excel con manejo robusto de errores"""
        try:
            self.ensure_one()
            
            # Validaciones adicionales para prevenir errores
            self._validate_export_parameters()
            
            # Construir dominio de búsqueda con validación
            domain = self._build_search_domain()
            
            # Obtener líneas con límite de seguridad
            lines = self._get_filtered_lines(domain)
            
            if not lines:
                return self._handle_no_data_error()
            
            # Actualizar fecha de cierre fiscal en las líneas si es necesario
            if self.fecha_cierre_fiscal:
                try:
                    lines.write({'fecha_cierre_fiscal': self.fecha_cierre_fiscal})
                except Exception as e:
                    _logger.warning(f"Could not update fecha_cierre_fiscal: {str(e)}")
            
            # Generar reporte con manejo de errores
            return self._generate_excel_report_safe(lines)
            
        except exceptions.UserError:
            # Re-raise user errors as they are expected
            raise
        except Exception as e:
            _logger.error(f"Unexpected error in export wizard: {str(e)}")
            raise exceptions.UserError(_(
                'Error inesperado durante la exportación. '
                'Por favor, contacte al administrador del sistema.\n'
                'Detalles técnicos: %s'
            ) % str(e))

    def _validate_export_parameters(self):
        """Validar parámetros de exportación para prevenir errores"""
        if not self.company_id:
            raise exceptions.UserError(_('La compañía es requerida para la exportación.'))
        
        if not self.currency_id:
            raise exceptions.UserError(_('La moneda es requerida para la exportación.'))
        
        if self.fecha_desde and self.fecha_hasta and self.fecha_desde > self.fecha_hasta:
            raise exceptions.UserError(_('La fecha desde no puede ser mayor que la fecha hasta.'))
        
        if self.ejercicio_fiscal < 1900 or self.ejercicio_fiscal > 2100:
            raise exceptions.UserError(_('El ejercicio fiscal debe estar entre 1900 y 2100.'))

    def _build_search_domain(self):
        """Construir dominio de búsqueda con validación"""
        domain = [('company_id', '=', self.company_id.id)]
        
        if self.fecha_desde:
            domain.append(('fecha_adquisicion', '>=', self.fecha_desde))
        if self.fecha_hasta:
            domain.append(('fecha_adquisicion', '<=', self.fecha_hasta))
        
        if self.solo_incluir_en_reporte:
            domain.append(('incluir_en_reporte', '=', True))
        
        if not self.incluir_dados_baja:
            domain.append(('baja_definitiva', '=', False))
        
        if not self.incluir_activos:
            domain.append(('activo', '=', False))
        
        return domain

    def _get_filtered_lines(self, domain):
        """Obtener líneas filtradas con límite de seguridad"""
        try:
            # Límite de seguridad para evitar consultas muy grandes
            MAX_RECORDS = 10000
            
            # Contar primero para verificar el tamaño
            count = self.env['resolucion.77.line'].search_count(domain)
            
            if count > MAX_RECORDS:
                raise exceptions.UserError(_(
                    'La consulta devuelve demasiados registros (%d). '
                    'Por favor, use filtros más restrictivos. '
                    'Máximo permitido: %d registros.'
                ) % (count, MAX_RECORDS))
            
            # Obtener líneas con orden específico
            lines = self.env['resolucion.77.line'].search(
                domain, 
                order='fecha_adquisicion, name',
                limit=MAX_RECORDS + 1  # +1 para detectar si hay más registros
            )
            
            return lines
            
        except exceptions.UserError:
            raise
        except Exception as e:
            _logger.error(f"Error getting filtered lines: {str(e)}")
            raise exceptions.UserError(_(
                'Error al obtener los datos para exportación: %s'
            ) % str(e))

    def _handle_no_data_error(self):
        """Manejar el caso cuando no hay datos para exportar"""
        message = _('No se encontraron líneas que cumplan con los criterios de filtro.\n\n')
        message += _('Sugerencias:\n')
        message += _('• Verifique las fechas de filtro\n')
        message += _('• Asegúrese de que existan registros marcados para reporte\n')
        message += _('• Revise los filtros de estado (activos/dados de baja)')
        
        raise exceptions.UserError(message)

    def _generate_excel_report_safe(self, lines):
        """Generar reporte Excel con manejo robusto de errores"""
        try:
            return self._generate_excel_report(lines)
        except MemoryError:
            raise exceptions.UserError(_(
                'Error de memoria durante la generación del reporte. '
                'Intente reducir el número de registros usando filtros.'
            ))
        except Exception as e:
            _logger.error(f"Error generating Excel report: {str(e)}")
            raise exceptions.UserError(_(
                'Error al generar el archivo Excel: %s'
            ) % str(e))

    def _generate_excel_report(self, lines):
        """Genera el reporte en Excel"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Cuadro Depreciación')
        
        # Configurar formatos
        self._setup_excel_formats(workbook)
        
        # Escribir contenido
        row = 0
        
        if self.incluir_encabezado_empresa:
            row = self._write_company_header(worksheet, workbook, row)
        
        row = self._write_report_title(worksheet, workbook, row)
        row = self._write_column_headers(worksheet, workbook, row)
        row = self._write_data_rows(worksheet, workbook, lines, row)
        
        if self.incluir_totales:
            row = self._write_totals_row(worksheet, workbook, lines, row)
        
        if self.incluir_fecha_generacion:
            self._write_footer(worksheet, workbook, row)
        
        workbook.close()
        output.seek(0)
        
        # Crear attachment
        filename = self._generate_filename()
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'store_fname': filename,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _setup_excel_formats(self, workbook):
        """Configura los formatos para Excel"""
        self.title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        self.subtitle_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'bg_color': '#E6F3FF',
            'border': 1
        })
        
        self.header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        self.currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        self.date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })
        
        self.percentage_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1
        })
        
        self.center_format = workbook.add_format({
            'align': 'center',
            'border': 1
        })
        
        self.text_format = workbook.add_format({
            'border': 1,
            'text_wrap': True
        })
        
        self.total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFEB9C',
            'border': 1,
            'num_format': '#,##0.00'
        })
        
        self.total_text_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFEB9C',
            'border': 1,
            'align': 'center'
        })

    def _write_company_header(self, worksheet, workbook, start_row):
        """Escribe el encabezado de la empresa"""
        company_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center'
        })
        
        worksheet.merge_range(start_row, 0, start_row, 8, 
                            f'{self.company_id.name}', company_format)
        worksheet.merge_range(start_row + 1, 0, start_row + 1, 8, 
                            f'RUC: {self.company_id.vat or "N/A"}', company_format)
        
        return start_row + 3

    def _write_report_title(self, worksheet, workbook, start_row):
        """Escribe el título del reporte"""
        title_text = (
            f'CUADRO DE DEPRECIACIÓN DE LOS BIENES DEL ACTIVO FIJO\n'
            f'RESOLUCIÓN GENERAL N° 77/2020 - SET\n'
            f'Ejercicio Fiscal {self.ejercicio_fiscal}'
        )
        
        worksheet.merge_range(start_row, 0, start_row + 2, 8, title_text, self.title_format)
        return start_row + 4

    def _write_column_headers(self, worksheet, workbook, start_row):
        """Escribe los encabezados de columnas"""
        headers = [
            'Código',
            'Descripción del Bien',
            'Fecha de\nAdquisición',
            'Valor de\nOrigen',
            '% Depreciación\nAnual',
            'Vida Útil\n(años)',
            'Depreciación\nAcumulada',
            'Valor Fiscal\nNeto al Cierre',
            'Valor Residual\nFiscal'
        ]
        
        # Configurar anchos de columna
        column_widths = [12, 35, 15, 15, 15, 12, 18, 18, 18]
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)
        
        for col, header in enumerate(headers):
            worksheet.write(start_row, col, header, self.header_format)
        
        return start_row + 1

    def _write_data_rows(self, worksheet, workbook, lines, start_row):
        """Escribe las filas de datos"""
        row = start_row
        
        for line in lines:
            worksheet.write(row, 0, line.codigo or '', self.text_format)
            worksheet.write(row, 1, line.name, self.text_format)
            worksheet.write(row, 2, line.fecha_adquisicion, self.date_format)
            worksheet.write(row, 3, line.valor_inicial, self.currency_format)
            worksheet.write(row, 4, line.porcentaje_depreciacion / 100, self.percentage_format)
            worksheet.write(row, 5, line.vida_util, self.center_format)
            worksheet.write(row, 6, line.depreciacion_acumulada, self.currency_format)
            worksheet.write(row, 7, line.valor_fiscal_neto, self.currency_format)
            worksheet.write(row, 8, line.valor_residual, self.currency_format)
            row += 1
        
        return row

    def _write_totals_row(self, worksheet, workbook, lines, start_row):
        """Escribe la fila de totales"""
        total_valor_origen = sum(lines.mapped('valor_inicial'))
        total_depreciacion_acumulada = sum(lines.mapped('depreciacion_acumulada'))
        total_valor_fiscal_neto = sum(lines.mapped('valor_fiscal_neto'))
        total_valor_residual = sum(lines.mapped('valor_residual'))
        
        worksheet.write(start_row, 0, '', self.total_text_format)
        worksheet.write(start_row, 1, 'TOTALES', self.total_text_format)
        worksheet.write(start_row, 2, '', self.total_text_format)
        worksheet.write(start_row, 3, total_valor_origen, self.total_format)
        worksheet.write(start_row, 4, '', self.total_text_format)
        worksheet.write(start_row, 5, '', self.total_text_format)
        worksheet.write(start_row, 6, total_depreciacion_acumulada, self.total_format)
        worksheet.write(start_row, 7, total_valor_fiscal_neto, self.total_format)
        worksheet.write(start_row, 8, total_valor_residual, self.total_format)
        
        return start_row + 1

    def _write_footer(self, worksheet, workbook, start_row):
        """Escribe el pie del reporte"""
        info_format = workbook.add_format({'italic': True, 'font_size': 10})
        
        row = start_row + 2
        worksheet.write(row, 0, f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', info_format)
        worksheet.write(row + 1, 0, f'Usuario: {self.env.user.name}', info_format)
        worksheet.write(row + 2, 0, f'Sistema: Odoo 18 - Módulo Resolución 77', info_format)

    def _generate_filename(self):
        """Genera el nombre del archivo"""
        fecha = datetime.now().strftime('%Y%m%d_%H%M')
        return f'Cuadro_Depreciacion_Resolucion77_{self.ejercicio_fiscal}_{fecha}.xlsx' 