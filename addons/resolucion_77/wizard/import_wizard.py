# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _
import base64
import io
import csv
from datetime import datetime


class Resolucion77ImportWizard(models.TransientModel):
    _name = 'resolucion.77.import.wizard'
    _description = 'Wizard de Importación Resolución 77'

    name = fields.Char(string="Nombre de Importación", default="Importación Masiva")
    
    # Archivo a importar
    archivo_csv = fields.Binary(string="Archivo CSV", required=True,
                               help="Archivo CSV con los datos de los bienes del activo fijo")
    nombre_archivo = fields.Char(string="Nombre del Archivo")
    
    # Configuración de importación
    separador = fields.Selection([
        (',', 'Coma (,)'),
        (';', 'Punto y coma (;)'),
        ('\t', 'Tabulación'),
        ('|', 'Pipe (|)')
    ], string="Separador", default=',', required=True)
    
    encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('latin-1', 'Latin-1'),
        ('cp1252', 'Windows-1252')
    ], string="Codificación", default='utf-8', required=True)
    
    tiene_encabezado = fields.Boolean(string="Archivo tiene encabezado", default=True)
    
    # Configuración por defecto para nuevos registros
    fecha_cierre_fiscal = fields.Date(string="Fecha de Cierre Fiscal por Defecto",
                                     default=lambda self: datetime(datetime.now().year, 12, 31).date())
    porcentaje_residual = fields.Float(string="% Valor Residual por Defecto", default=10.0)
    incluir_en_reporte = fields.Boolean(string="Incluir en Reporte por Defecto", default=True)
    activo = fields.Boolean(string="Marcar como Activo por Defecto", default=True)
    
    # Opciones de importación
    actualizar_existentes = fields.Boolean(string="Actualizar Registros Existentes", default=False,
                                          help="Si está marcado, actualiza registros existentes basándose en el código")
    crear_categorias = fields.Boolean(string="Crear Categorías Automáticamente", default=True,
                                     help="Crear categorías de activos si no existen")
    
    # Resultados de la importación
    estado = fields.Selection([
        ('draft', 'Borrador'),
        ('validating', 'Validando'),
        ('ready', 'Listo para Importar'),
        ('imported', 'Importado'),
        ('error', 'Error')
    ], string="Estado", default='draft', readonly=True)
    
    registros_procesados = fields.Integer(string="Registros Procesados", readonly=True)
    registros_creados = fields.Integer(string="Registros Creados", readonly=True)
    registros_actualizados = fields.Integer(string="Registros Actualizados", readonly=True)
    registros_error = fields.Integer(string="Registros con Error", readonly=True)
    
    log_errores = fields.Text(string="Log de Errores", readonly=True)
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                                default=lambda self: self.env.company)

    def action_validate_file(self):
        """Valida el archivo CSV"""
        self.ensure_one()
        
        if not self.archivo_csv:
            raise exceptions.UserError(_('Debe seleccionar un archivo CSV'))
        
        try:
            # Decodificar el archivo
            file_data = base64.b64decode(self.archivo_csv)
            file_content = file_data.decode(self.encoding)
            
            # Leer CSV
            csv_reader = csv.reader(io.StringIO(file_content), delimiter=self.separador)
            rows = list(csv_reader)
            
            if not rows:
                raise exceptions.UserError(_('El archivo está vacío'))
            
            # Validar estructura
            expected_columns = self._get_expected_columns()
            
            if self.tiene_encabezado:
                header_row = rows[0]
                data_rows = rows[1:]
                
                # Validar que tenga al menos las columnas mínimas
                if len(header_row) < len(expected_columns):
                    raise exceptions.UserError(
                        _('El archivo debe tener al menos %d columnas. Columnas esperadas: %s') % 
                        (len(expected_columns), ', '.join(expected_columns))
                    )
            else:
                data_rows = rows
            
            if not data_rows:
                raise exceptions.UserError(_('No hay datos para importar'))
            
            # Validar algunas filas de muestra
            errors = []
            for i, row in enumerate(data_rows[:5]):  # Validar solo las primeras 5 filas
                try:
                    self._validate_row(row)
                except Exception as e:
                    errors.append(f'Fila {i+2}: {str(e)}')
            
            if errors:
                self.log_errores = '\n'.join(errors)
                self.estado = 'error'
                raise exceptions.UserError(
                    _('Se encontraron errores en el archivo:\n%s') % '\n'.join(errors)
                )
            
            self.registros_procesados = len(data_rows)
            self.estado = 'ready'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Validación Exitosa'),
                    'message': _('El archivo es válido. %d registros listos para importar.') % len(data_rows),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            self.estado = 'error'
            self.log_errores = str(e)
            raise exceptions.UserError(_('Error al validar el archivo: %s') % str(e))

    def action_import_data(self):
        """Importa los datos del archivo CSV"""
        self.ensure_one()
        
        if self.estado != 'ready':
            raise exceptions.UserError(_('Debe validar el archivo antes de importar'))
        
        try:
            # Decodificar el archivo
            file_data = base64.b64decode(self.archivo_csv)
            file_content = file_data.decode(self.encoding)
            
            # Leer CSV
            csv_reader = csv.reader(io.StringIO(file_content), delimiter=self.separador)
            rows = list(csv_reader)
            
            if self.tiene_encabezado:
                data_rows = rows[1:]
            else:
                data_rows = rows
            
            # Procesar filas
            created_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            
            for i, row in enumerate(data_rows):
                try:
                    result = self._process_row(row)
                    if result == 'created':
                        created_count += 1
                    elif result == 'updated':
                        updated_count += 1
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f'Fila {i+2}: {str(e)}')
            
            # Actualizar estadísticas
            self.registros_creados = created_count
            self.registros_actualizados = updated_count
            self.registros_error = error_count
            
            if errors:
                self.log_errores = '\n'.join(errors)
            
            self.estado = 'imported'
            
            message = _('Importación completada:\n- Creados: %d\n- Actualizados: %d\n- Errores: %d') % (
                created_count, updated_count, error_count
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importación Completada'),
                    'message': message,
                    'type': 'success' if error_count == 0 else 'warning',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            self.estado = 'error'
            self.log_errores = str(e)
            raise exceptions.UserError(_('Error durante la importación: %s') % str(e))

    def _get_expected_columns(self):
        """Devuelve las columnas esperadas en el CSV"""
        return [
            'codigo',
            'descripcion',
            'fecha_adquisicion',
            'valor_inicial',
            'porcentaje_depreciacion',
            'vida_util',
            'categoria',
            'numero_factura',
            'proveedor'
        ]

    def _validate_row(self, row):
        """Valida una fila del CSV"""
        if len(row) < 6:  # Mínimo: código, descripción, fecha, valor, porcentaje, vida_util
            raise exceptions.ValidationError(_('La fila debe tener al menos 6 columnas'))
        
        # Validar fecha
        if row[2]:  # fecha_adquisicion
            try:
                datetime.strptime(row[2], '%d/%m/%Y')
            except ValueError:
                raise exceptions.ValidationError(_('Fecha de adquisición inválida (formato esperado: DD/MM/YYYY)'))
        
        # Validar valor inicial
        if row[3]:  # valor_inicial
            try:
                float(row[3].replace(',', '.'))
            except ValueError:
                raise exceptions.ValidationError(_('Valor inicial inválido'))
        
        # Validar porcentaje
        if row[4]:  # porcentaje_depreciacion
            try:
                porcentaje = float(row[4].replace(',', '.'))
                if porcentaje < 0 or porcentaje > 100:
                    raise exceptions.ValidationError(_('El porcentaje debe estar entre 0 y 100'))
            except ValueError:
                raise exceptions.ValidationError(_('Porcentaje de depreciación inválido'))
        
        # Validar vida útil
        if row[5]:  # vida_util
            try:
                vida_util = int(row[5])
                if vida_util <= 0:
                    raise exceptions.ValidationError(_('La vida útil debe ser mayor a 0'))
            except ValueError:
                raise exceptions.ValidationError(_('Vida útil inválida'))

    def _process_row(self, row):
        """Procesa una fila del CSV y crea/actualiza el registro"""
        # Preparar datos
        codigo = row[0].strip() if row[0] else ''
        descripcion = row[1].strip() if len(row) > 1 and row[1] else ''
        fecha_adquisicion = datetime.strptime(row[2], '%d/%m/%Y').date() if len(row) > 2 and row[2] else None
        valor_inicial = float(row[3].replace(',', '.')) if len(row) > 3 and row[3] else 0
        porcentaje_depreciacion = float(row[4].replace(',', '.')) if len(row) > 4 and row[4] else 0
        vida_util = int(row[5]) if len(row) > 5 and row[5] else 0
        categoria = row[6].strip() if len(row) > 6 and row[6] else 'otros'
        numero_factura = row[7].strip() if len(row) > 7 and row[7] else ''
        proveedor_name = row[8].strip() if len(row) > 8 and row[8] else ''
        
        # Buscar proveedor
        proveedor_id = False
        if proveedor_name:
            proveedor = self.env['res.partner'].search([
                ('name', 'ilike', proveedor_name),
                ('is_company', '=', True)
            ], limit=1)
            if proveedor:
                proveedor_id = proveedor.id
        
        # Preparar valores
        vals = {
            'name': descripcion,
            'codigo': codigo,
            'fecha_adquisicion': fecha_adquisicion,
            'valor_inicial': valor_inicial,
            'porcentaje_depreciacion': porcentaje_depreciacion,
            'vida_util': vida_util,
            'categoria_activo': categoria,
            'numero_factura': numero_factura,
            'proveedor_id': proveedor_id,
            'fecha_cierre_fiscal': self.fecha_cierre_fiscal,
            'porcentaje_residual': self.porcentaje_residual,
            'incluir_en_reporte': self.incluir_en_reporte,
            'activo': self.activo,
            'company_id': self.company_id.id,
        }
        
        # Buscar registro existente
        existing = None
        if codigo and self.actualizar_existentes:
            existing = self.env['resolucion.77.line'].search([
                ('codigo', '=', codigo),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        
        if existing:
            existing.write(vals)
            return 'updated'
        else:
            self.env['resolucion.77.line'].create(vals)
            return 'created'

    def action_download_template(self):
        """Descargar plantilla CSV"""
        # Crear contenido CSV de ejemplo
        csv_content = "codigo,descripcion,fecha_adquisicion,valor_inicial,porcentaje_depreciacion,vida_util,categoria,numero_factura,proveedor\n"
        csv_content += "EQ001,Computadora Dell,01/01/2023,1500000,25,4,equipos_computo,001-001-0000123,Proveedor Ejemplo\n"
        csv_content += "VH001,Vehículo Toyota,15/03/2023,45000000,20,5,vehiculos,001-001-0000124,Concesionario XYZ\n"
        
        # Codificar a base64
        csv_encoded = base64.b64encode(csv_content.encode('utf-8'))
        
        # Crear attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_resolucion77.csv',
            'type': 'binary',
            'datas': csv_encoded,
            'store_fname': 'plantilla_resolucion77.csv',
            'mimetype': 'text/csv'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        } 