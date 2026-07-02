# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _
from odoo.exceptions import UserError
from datetime import datetime, date
import xlsxwriter
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class Resolucion77Line(models.Model):
    _name = 'resolucion.77.line'
    _description = 'Cuadro de Depreciación - Resolución 77 SET'
    _order = 'fecha_adquisicion desc, name'
    _rec_name = 'name'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos del bien
    name = fields.Char(
        string="Descripción del Bien", 
        required=True, 
        help="Descripción detallada del bien del activo fijo",
        tracking=True
    )
    codigo = fields.Char(
        string="Código Interno", 
        help="Código interno o número de inventario del bien",
        index=True
    )
    
    # Información de adquisición
    fecha_adquisicion = fields.Date(
        string="Fecha de Adquisición", 
        required=True,
        help="Fecha en que se adquirió el bien",
        tracking=True,
        index=True
    )
    valor_inicial = fields.Monetary(
        string="Valor de Origen", 
        required=True, 
        currency_field='currency_id',
        help="Valor de adquisición o costo histórico del bien",
        tracking=True
    )
    
    # Configuración de depreciación
    porcentaje_depreciacion = fields.Float(string="% Depreciación Anual", required=True,
                                          help="Porcentaje de depreciación anual según la SET")
    vida_util = fields.Integer(string="Vida Útil (años)", required=True,
                              help="Vida útil estimada del bien en años")
    metodo = fields.Selection([
        ('lineal', 'Método Lineal')
    ], default='lineal', string="Método de Depreciación", required=True)
    
    # Campos calculados
    depreciacion_anual = fields.Monetary(string="Depreciación Anual", 
                                        compute='_compute_depreciacion_anual',
                                        currency_field='currency_id', store=True,
                                        help="Monto de depreciación anual calculada")
    depreciacion_mensual = fields.Monetary(string="Depreciación Mensual",
                                        compute='_compute_depreciacion_anual',
                                        currency_field='currency_id', store=True,
                                        help="Monto de depreciación mensual calculada")
    depreciacion_acumulada = fields.Monetary(string="Depreciación Acumulada", 
                                            compute='_compute_depreciacion_acumulada',
                                            currency_field='currency_id', store=True,
                                            help="Depreciación acumulada hasta la fecha")
    valor_fiscal_neto = fields.Monetary(string="Valor Fiscal Neto al Cierre", 
                                       compute='_compute_valor_fiscal_neto',
                                       currency_field='currency_id', store=True,
                                       help="Valor contable neto al cierre del ejercicio")
    valor_residual = fields.Monetary(string="Valor Residual Fiscal", 
                                    compute='_compute_valor_residual',
                                    currency_field='currency_id', store=True,
                                    help="Valor residual fiscal según normativa SET")
    
    # Configuración del cálculo
    fecha_cierre_fiscal = fields.Date(string="Fecha de Cierre Fiscal", 
                                     default=lambda self: date(date.today().year, 12, 31),
                                     help="Fecha de cierre del ejercicio fiscal (31/12, 30/04 o 30/06)")
    porcentaje_residual = fields.Float(string="% Valor Residual", default=10.0,
                                      help="Porcentaje para calcular el valor residual (default 10%)")
    
    # Estado y control
    activo = fields.Boolean(
        string="Activo", 
        default=True,
        help="Indica si el bien está activo o fue dado de baja",
        tracking=True
    )
    incluir_en_reporte = fields.Boolean(
        string="Incluir en Reporte", 
        default=True,
        help="Incluir este bien en los reportes de Resolución 77",
        tracking=True
    )
    baja_definitiva = fields.Boolean(string="Baja Definitiva", default=False,
                                    help="Marcar si el bien fue dado de baja definitivamente")
    fecha_baja = fields.Date(string="Fecha de Baja",
                            help="Fecha en que se dio de baja el bien")
    
    # Información adicional
    numero_factura = fields.Char(string="Número de Factura",
                                help="Número de factura de adquisición")
    proveedor_id = fields.Many2one('res.partner', string="Proveedor",
                                  help="Proveedor del bien")
    categoria_activo = fields.Selection([
        ('edificios', 'Edificios y Construcciones'),
        ('maquinaria', 'Maquinaria y Equipos'),
        ('vehiculos', 'Vehículos'),
        ('muebles', 'Muebles y Enseres'),
        ('equipos_computo', 'Equipos de Cómputo'),
        ('otros', 'Otros Activos Fijos')
    ], string="Categoría de Activo", help="Categoría del activo fijo")
    
    # Adjuntos
    documento_respaldo = fields.Binary(string="Documento de Respaldo",
                                      help="Factura, contrato u otro documento de respaldo")
    nombre_documento = fields.Char(string="Nombre del Documento")
    
    # Moneda y compañía
    currency_id = fields.Many2one(
        'res.currency', 
        string='Moneda', 
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        default=lambda self: self.env.company,
        required=True,
        index=True
    )

    # ========== NUEVOS CAMPOS PARA INTEGRACIÓN CONTABLE ==========
    
    # Integración con Activos Fijos
    asset_id = fields.Many2one('account.asset', string="Activo Fijo Contable",
                               help="Activo fijo creado en el sistema contable")
    asset_created = fields.Boolean(string="Activo Fijo Creado", default=False,
                                  help="Indica si se ha creado el activo fijo en contabilidad")
    
    # Integración con Asientos Contables
    move_ids = fields.One2many('account.move', 'resolucion_77_line_id', 
                               string="Asientos Contables",
                               help="Asientos contables generados para este bien")
    move_count = fields.Integer(string="Cantidad de Asientos", 
                               compute='_compute_move_count')
    
    # Configuración contable
    account_asset_id = fields.Many2one('account.account', string="Cuenta de Activo",
                                       domain=[('account_type', '=', 'asset_fixed')],
                                       help="Cuenta contable del activo fijo")
    account_depreciation_id = fields.Many2one('account.account', string="Cuenta de Depreciación Acumulada",
                                             domain=[('account_type', '=', 'asset_fixed')],
                                             help="Cuenta de depreciación acumulada")
    account_depreciation_expense_id = fields.Many2one('account.account', string="Cuenta de Gastos de Depreciación",
                                                     domain=[('account_type', '=', 'expenses')],
                                                     help="Cuenta de gastos de depreciación")
    journal_id = fields.Many2one('account.journal', string="Diario de Depreciación",
                                 domain=[('type', '=', 'general')],
                                 help="Diario para registrar asientos de depreciación")

    # ========== RESTRICCIONES SQL ==========
    _sql_constraints = [
        ('codigo_company_unique', 'unique(codigo, company_id)', 
         'El código del bien debe ser único por compañía (dejar vacío si no aplica).'),
        ('valor_inicial_positive', 'check(valor_inicial > 0)', 
         'El valor inicial debe ser mayor a cero.'),
        ('porcentaje_depreciacion_valid', 'check(porcentaje_depreciacion >= 0 AND porcentaje_depreciacion <= 100)', 
         'El porcentaje de depreciación debe estar entre 0% y 100%.'),
        ('vida_util_positive', 'check(vida_util > 0)', 
         'La vida útil debe ser mayor a cero.'),
        ('porcentaje_residual_valid', 'check(porcentaje_residual >= 0 AND porcentaje_residual <= 100)', 
         'El porcentaje residual debe estar entre 0% y 100%.'),
    ]

    # ========== MÉTODOS COMPUTADOS ==========

    @api.depends('move_ids')
    def _compute_move_count(self):
        """Calcula la cantidad de asientos contables"""
        for record in self:
            record.move_count = len(record.move_ids)

    @api.depends('valor_inicial', 'porcentaje_depreciacion', 'vida_util', 'porcentaje_residual', 'valor_residual')
    def _compute_depreciacion_anual(self):
        """Calcula la depreciación anual"""
        for record in self:
            if record.valor_inicial and record.vida_util:
                # La base depreciable es Valor Inicial - Valor Residual
                base_depreciable = record.valor_inicial - record.valor_residual
                
                # Depreciación anual = Base / Vida Útil
                if record.vida_util > 0:
                    record.depreciacion_anual = base_depreciable / record.vida_util
                else:
                    record.depreciacion_anual = 0.0
                    
                record.depreciacion_mensual = record.depreciacion_anual / 12
            else:
                record.depreciacion_anual = 0.0
                record.depreciacion_mensual = 0.0

    @api.depends('depreciacion_anual', 'fecha_adquisicion', 'fecha_cierre_fiscal', 'activo')
    def _compute_depreciacion_acumulada(self):
        """Calcula la depreciación acumulada hasta la fecha de cierre fiscal"""
        for record in self:
            if not record.fecha_adquisicion or not record.fecha_cierre_fiscal or not record.activo:
                record.depreciacion_acumulada = 0.0
                continue
                
            # Calcular años completos entre adquisición y cierre fiscal
            anos_transcurridos = (record.fecha_cierre_fiscal - record.fecha_adquisicion).days / 365.25
            anos_depreciar = min(anos_transcurridos, record.vida_util or 0)
            
            if anos_depreciar > 0:
                record.depreciacion_acumulada = record.depreciacion_anual * round(anos_depreciar, 5)
            else:
                record.depreciacion_acumulada = 0.0

    @api.depends('valor_inicial', 'depreciacion_acumulada')
    def _compute_valor_fiscal_neto(self):
        """Calcula el valor fiscal neto al cierre"""
        for record in self:
            record.valor_fiscal_neto = record.valor_inicial - record.depreciacion_acumulada

    @api.depends('valor_inicial', 'porcentaje_residual')
    def _compute_valor_residual(self):
        """Calcula el valor residual fiscal basado en el porcentaje residual"""
        for record in self:
            if record.valor_inicial and record.porcentaje_residual:
                record.valor_residual = record.valor_inicial * (record.porcentaje_residual / 100)
            else:
                record.valor_residual = 0.0

    # ========== VALIDACIONES ==========

    @api.constrains('porcentaje_depreciacion')
    def _check_porcentaje_depreciacion(self):
        """Valida que el porcentaje de depreciación esté en un rango válido"""
        for record in self:
            if record.porcentaje_depreciacion < 0 or record.porcentaje_depreciacion > 100:
                raise exceptions.ValidationError(
                    _('El porcentaje de depreciación debe estar entre 0% y 100%')
                )

    @api.constrains('vida_util')
    def _check_vida_util(self):
        """Valida que la vida útil sea mayor a 0"""
        for record in self:
            if record.vida_util <= 0:
                raise exceptions.ValidationError(
                    _('La vida útil debe ser mayor a 0 años')
                )

    @api.constrains('valor_inicial')
    def _check_valor_inicial(self):
        """Valida que el valor inicial sea mayor a 0"""
        for record in self:
            if record.valor_inicial <= 0:
                raise exceptions.ValidationError(
                    _('El valor de origen debe ser mayor a 0')
                )

    @api.constrains('fecha_adquisicion', 'fecha_cierre_fiscal')
    def _check_fechas(self):
        """Valida que la fecha de adquisición no sea posterior al cierre fiscal"""
        for record in self:
            if record.fecha_adquisicion and record.fecha_cierre_fiscal:
                if record.fecha_adquisicion > record.fecha_cierre_fiscal:
                    raise exceptions.ValidationError(
                        _('La fecha de adquisición no puede ser posterior a la fecha de cierre fiscal')
                    )

    @api.onchange('categoria_activo')
    def _onchange_categoria_activo(self):
        """Si se cambia la categoría, sugerir porcentajes y vida útil de la configuración"""
        if self.categoria_activo:
            config = self.env['resolucion.77.config'].get_default_config()
            if config:
                self.porcentaje_depreciacion = config.get_porcentaje_por_categoria(self.categoria_activo)
                self.vida_util = config.get_vida_util_por_categoria(self.categoria_activo)
                self.porcentaje_residual = config.porcentaje_residual_default

    # ========== NUEVOS MÉTODOS PARA INTEGRACIÓN CONTABLE ==========

    def action_create_asset(self):
        """Crea un activo fijo en el sistema contable"""
        self.ensure_one()
        
        if self.asset_created:
            raise exceptions.UserError(_('El activo fijo ya ha sido creado'))
        
        if not self.account_asset_id:
            raise exceptions.UserError(_('Debe configurar la cuenta de activo'))
        
        # Crear el activo fijo en Odoo 18
        # En Odoo 18, method_period '1' es mensual, '12' es anual.
        # Si queremos depreciar por vida_util años mensualmente:
        asset_vals = {
            'name': self.name,
            'original_value': self.valor_inicial,
            'salvage_value': self.valor_residual,
            'acquisition_date': self.fecha_adquisicion,
            'method': 'linear',
            'method_period': '1',  # Mensual
            'method_number': self.vida_util * 12,  # Número de meses
            'account_asset_id': self.account_asset_id.id,
            'account_depreciation_id': self.account_depreciation_id.id,
            'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'state': 'draft',
        }
        
        asset = self.env['account.asset'].create(asset_vals)
        
        # Actualizar registro
        self.write({
            'asset_id': asset.id,
            'asset_created': True
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'res_id': asset.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_asset(self):
        """Abre la vista del activo fijo asociado"""
        self.ensure_one()
        
        if not self.asset_id:
            raise exceptions.UserError(_('No hay activo fijo asociado'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Activo Fijo'),
            'res_model': 'account.asset',
            'res_id': self.asset_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_generate_depreciation_move(self):
        """Genera el asiento contable de depreciación"""
        self.ensure_one()
        
        if not self.asset_created:
            raise exceptions.UserError(_('Debe crear el activo fijo primero'))
        
        if not self.journal_id:
            raise exceptions.UserError(_('Debe configurar el diario de depreciación'))
        
        if not self.account_depreciation_expense_id or not self.account_depreciation_id:
            raise exceptions.UserError(_('Debe configurar las cuentas contables'))
        
        # Crear asiento contable
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.fecha_cierre_fiscal,
            'ref': f'Depreciación {self.name} - {self.fecha_cierre_fiscal.year}',
            'resolucion_77_line_id': self.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_depreciation_expense_id.id,
                    'debit': self.depreciacion_anual,
                    'credit': 0.0,
                    'name': f'Gasto de depreciación - {self.name}',
                    'partner_id': self.proveedor_id.id if self.proveedor_id else False,
                }),
                (0, 0, {
                    'account_id': self.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': self.depreciacion_anual,
                    'name': f'Depreciación acumulada - {self.name}',
                    'partner_id': self.proveedor_id.id if self.proveedor_id else False,
                })
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_moves(self):
        """Vista de asientos contables"""
        self.ensure_one()
        
        return {
            'name': _('Asientos Contables'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('resolucion_77_line_id', '=', self.id)],
            'context': {'default_resolucion_77_line_id': self.id},
            'target': 'current',
    }

    def _get_or_create_asset_category(self):
        """Obtiene o crea la configuración por defecto para activos"""
        # En Odoo 18, no necesitamos categorías de activos específicas
        # El activo se crea directamente con la configuración
        return True

    # ========== MÉTODOS EXISTENTES ==========

    def action_dar_de_baja(self):
        """Acción para dar de baja un bien"""
        self.ensure_one()
        raise UserError(f'{_("Funcionalidad de dar de baja aún no implementada. Próximamente.")}')
        # return {
        #     'name': _('Dar de Baja Bien'),
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'resolucion.77.baja.wizard',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {'default_line_id': self.id}
        # }

    def action_reactivar(self):
        """Reactivar un bien dado de baja"""
        self.write({
            'activo': True,
            'baja_definitiva': False,
            'fecha_baja': False
        })

    def export_cuadro_depreciacion(self):
        """Exporta el cuadro de depreciación a Excel"""
        # Obtener todas las líneas activas para el reporte
        lines = self.search([
            ('incluir_en_reporte', '=', True),
            ('company_id', '=', self.env.company.id)
        ])
        
        if not lines:
            raise exceptions.UserError(_('No hay líneas para exportar'))
        
        return lines._generate_excel_report()

    def _generate_excel_report(self):
        """Genera el reporte en Excel con formato oficial de la SET"""
        # Crear archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Cuadro Depreciación')
        
        # Configurar formatos
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E6F3FF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })
        
        percentage_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1
        })
        
        center_format = workbook.add_format({
            'align': 'center',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1,
            'text_wrap': True
        })
        
        # Título principal
        worksheet.merge_range('A1:I2', 
            f'CUADRO DE DEPRECIACIÓN DE LOS BIENES DEL ACTIVO FIJO\n'
            f'RESOLUCIÓN GENERAL N° 77/2020 - SET\n'
            f'Ejercicio Fiscal {self[0].fecha_cierre_fiscal.year if self else datetime.now().year}', 
            title_format)
        
        # Headers de columnas (fila 4)
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
        
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_format)
        
        # Ajustar anchos de columna
        column_widths = [12, 35, 15, 15, 15, 12, 18, 18, 18]
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)
        
        # Datos de las líneas
        row = 4
        total_valor_origen = 0
        total_depreciacion_acumulada = 0
        total_valor_fiscal_neto = 0
        total_valor_residual = 0
        
        for line in self:
            if not line.incluir_en_reporte:
                continue
                
            worksheet.write(row, 0, line.codigo or '', text_format)
            worksheet.write(row, 1, line.name, text_format)
            worksheet.write(row, 2, line.fecha_adquisicion, date_format)
            worksheet.write(row, 3, line.valor_inicial, currency_format)
            worksheet.write(row, 4, line.porcentaje_depreciacion / 100, percentage_format)
            worksheet.write(row, 5, line.vida_util, center_format)
            worksheet.write(row, 6, line.depreciacion_acumulada, currency_format)
            worksheet.write(row, 7, line.valor_fiscal_neto, currency_format)
            worksheet.write(row, 8, line.valor_residual, currency_format)
            
            # Acumular totales
            total_valor_origen += line.valor_inicial
            total_depreciacion_acumulada += line.depreciacion_acumulada
            total_valor_fiscal_neto += line.valor_fiscal_neto
            total_valor_residual += line.valor_residual
            
            row += 1
        
        # Fila de totales
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFEB9C',
            'border': 1,
            'num_format': '#,##0.00'
        })
        
        total_text_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFEB9C',
            'border': 1,
            'align': 'center'
        })
        
        worksheet.write(row, 0, '', total_text_format)
        worksheet.write(row, 1, 'TOTALES', total_text_format)
        worksheet.write(row, 2, '', total_text_format)
        worksheet.write(row, 3, total_valor_origen, total_format)
        worksheet.write(row, 4, '', total_text_format)
        worksheet.write(row, 5, '', total_text_format)
        worksheet.write(row, 6, total_depreciacion_acumulada, total_format)
        worksheet.write(row, 7, total_valor_fiscal_neto, total_format)
        worksheet.write(row, 8, total_valor_residual, total_format)
        
        # Información adicional
        row += 3
        info_format = workbook.add_format({'italic': True, 'font_size': 10})
        worksheet.write(row, 0, f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', info_format)
        worksheet.write(row + 1, 0, f'Compañía: {self.env.company.name}', info_format)
        worksheet.write(row + 2, 0, f'RUC: {self.env.company.vat or "N/A"}', info_format)
        
        workbook.close()
        output.seek(0)
        
        # Crear attachment
        fecha = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f'Cuadro_Depreciacion_Resolucion77_{fecha}.xlsx'
        
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
