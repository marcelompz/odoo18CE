# -*- coding: utf-8 -*-

from odoo import models, fields, api, release
import xlsxwriter
import base64


class WizardReporteCompra(models.TransientModel):
    _name = 'reporte_compraventa.wizardcompra'
    _description = 'Asistente para Reporte de Compras'

    fecha_inicio = fields.Date(string='Fecha Inicio', required=True)
    fecha_fin = fields.Date(string='Fecha Fin', required=True)

    def print_report_xlsx(self):
        """Generar reporte Excel de compras usando controlador personalizado"""
        self.ensure_one()
        
        # Usar controlador personalizado para generar Excel (patrón Odoo 18)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/reporte_compraventa/compras/xlsx/{self.id}',
            'target': 'new',
        }


class ReporteComprasXLSX(models.AbstractModel):
    _name = 'report.reporte_compraventa.reporte_compra_xlsx'
    _description = 'Reporte de Compras en formato XLSX'
    _inherit = 'report.report_xlsx.abstract'

    def get_facturas_libro_compra(self, fecha_inicio, fecha_fin):
        """Obtiene las facturas de compra publicadas en el período"""
        return self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('invoice_number', '!=', False),
            ('invoice_date', '>=', fecha_inicio),
            ('invoice_date', '<=', fecha_fin),
            ('company_id', '=', self.env.company.id),
        ])

    def get_notas_credito_compra(self, fecha_inicio, fecha_fin):
        """Obtiene las notas de crédito de compra publicadas en el período"""
        return self.env['account.move'].search([
            ('move_type', '=', 'in_refund'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', fecha_inicio),
            ('invoice_date', '<=', fecha_fin),
            ('company_id', '=', self.env.company.id),
        ])

    def calcular_impuestos_linea(self, invoice_line):
        """Calcula los impuestos para una línea de factura"""
        base10 = 0
        iva10 = 0
        base5 = 0
        iva5 = 0
        exentas = 0
        
        if invoice_line.tax_ids:
            for tax in invoice_line.tax_ids:
                if tax.amount == 10:
                    base10 += invoice_line.price_subtotal
                    iva10 += invoice_line.price_subtotal * 0.10
                elif tax.amount == 5:
                    base5 += invoice_line.price_subtotal
                    iva5 += invoice_line.price_subtotal * 0.05
                elif tax.amount == 0:
                    exentas += invoice_line.price_subtotal
        else:
            # Si no hay impuestos, se considera exenta
            exentas += invoice_line.price_subtotal

        return base10, iva10, base5, iva5, exentas

    def get_tipo_comprobante(self, move):
        """Determina el tipo de comprobante"""
        if move.move_type == 'in_invoice':
            return 'Factura'
        elif move.move_type == 'in_refund':
            return 'Nota de Crédito'
        elif move.move_type == 'in_debit':
            return 'Nota de Débito'
        else:
            return 'Otro'

    def get_condicion_pago(self, move):
        """Determina si es contado o crédito"""
        if move.invoice_date and move.invoice_date_due:
            if move.invoice_date < move.invoice_date_due:
                return 'Crédito'
            else:
                return 'Contado'
        return 'Contado'

    def get_tipo_cambio(self, move):
        """
        Obtiene el tipo de cambio de forma legible (ej. 6900 en lugar de 0.00014).
        Funciona para:
        - Empresa PYG / Factura USD
        - Empresa USD / Factura PYG
        """
        # 1. Si las monedas son iguales, el cambio es 1.0
        if move.currency_id == self.env.company.currency_id:
            return 1.0

        for line in move.line_ids:
            # Buscamos una línea que tenga montos para poder calcular
            if line.amount_currency and line.balance:
                
                # 2. Calculamos el factor crudo de Odoo
                tasa_calculada = abs(line.balance / line.amount_currency)
                
                # 3. Lógica de inversión inteligente:
                # Si la tasa es muy pequeña (ej: 0.000145), significa que estamos 
                # convirtiendo de Moneda Débil (PYG) a Fuerte (USD).
                # Para verlo "humano" (6880), invertimos la división.
                if tasa_calculada < 1.0 and tasa_calculada > 0:
                    return 1.0 / tasa_calculada
                
                # Si la tasa es grande (ej: 6880), significa que es USD -> PYG. 
                # Ya está en el formato correcto.
                return tasa_calculada
                
        return 1.0

    def generate_xlsx_report(self, workbook, data, datas):
        """Genera el reporte XLSX de compras"""
        # definimos la moneda PYG
        pyg_currency = self.env['res.currency'].search([('name', '=', 'PYG')], limit=1)

        # 1. Determinar el formato de moneda base
        company_currency = self.env.company.currency_id
        
        # Construcción dinámica basada en decimal_places
        n_decimals = company_currency.decimal_places
        decimal_part = '.' + ('0' * n_decimals) if n_decimals > 0 else ''
        str_format_montos = f'#,##0{decimal_part}'
        
        # Configuración de formatos
        bold = workbook.add_format({'bold': True})
        
        # Formatos numéricos dinámicos
        numerico_montos = workbook.add_format({'num_format': str_format_montos, 'align': 'right'})
        numerico_total = workbook.add_format({'num_format': str_format_montos, 'align': 'right', 'bold': True})
        
        # Formato TC fijo con 2 decimales
        numerico_tc = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        
        wrapped_text = workbook.add_format({'text_wrap': True})
        wrapped_text_bold = workbook.add_format({'text_wrap': True, 'bold': True})
        fecha_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
        # Crear hoja de trabajo
        sheet = workbook.add_worksheet('Libro IVA Compras')
        
        # Configurar ancho de columnas
        sheet.set_column('A:A', 8)   # Nro
        sheet.set_column('B:B', 12)  # Fecha
        sheet.set_column('C:C', 15)  # Tipo
        sheet.set_column('D:D', 25)  # Tipo Documento
        sheet.set_column('E:E', 20)  # Número
        sheet.set_column('F:F', 30)  # Proveedor
        sheet.set_column('G:G', 15)  # RUC
        sheet.set_column('H:H', 10)  # Condición
        sheet.set_column('I:I', 8)   # Moneda
        sheet.set_column('J:J', 10)  # T.C.
        sheet.set_column('K:K', 15)  # Base 10%
        sheet.set_column('L:L', 12)  # IVA 10%
        sheet.set_column('M:M', 15)  # Base 5%
        sheet.set_column('N:N', 12)  # IVA 5%
        sheet.set_column('O:O', 12)  # Exentas
        sheet.set_column('P:P', 15)  # Total
        sheet.set_column('Q:Q', 15)  # Crédito Fiscal

        # Encabezado del reporte
        row = 0
        sheet.write(row, 0, "Razón social:", bold)
        sheet.write(row, 1, self.env.company.name)
        row += 1
        sheet.write(row, 0, "RUC:", bold)
        sheet.write(row, 1, self.env.company.partner_id.vat or '')
        row += 1
        sheet.write(row, 0, "Período:", bold)
        sheet.write(row, 1, f"Del {datas.fecha_inicio.strftime('%d/%m/%Y')} al {datas.fecha_fin.strftime('%d/%m/%Y')}")
        row += 2

        # Título del libro
        sheet.write(row, 0, "LIBRO IVA COMPRAS - LEY 125/91", bold)
        row += 1

        # Encabezados de columnas
        headers = [
            "Nro", "Fecha", "Tipo", "Tipo Documento", "Número", "Proveedor", 
            "RUC", "Condición", "Moneda", "T.C.", "Base 10%", "IVA 10%", 
            "Base 5%", "IVA 5%", "Exentas", "Total", "Crédito Fiscal"
        ]
        
        for col, header in enumerate(headers):
            sheet.write(row, col, header, wrapped_text_bold)
        row += 1

        # Obtener facturas y notas de crédito
        facturas = self.get_facturas_libro_compra(datas.fecha_inicio, datas.fecha_fin)
        notas_credito = self.get_notas_credito_compra(datas.fecha_inicio, datas.fecha_fin)
        
        # Variables para totales
        totales = {
            'base10': 0, 'iva10': 0, 'base5': 0, 'iva5': 0, 
            'exentas': 0, 'total': 0, 'credito_fiscal': 0
        }

        # --- PROCESAR FACTURAS ---
        contador = 1
        for factura in facturas.sorted(lambda m: (m.invoice_date, m.name)):
            base10, iva10, base5, iva5, exentas = 0, 0, 0, 0, 0
            
            for linea in factura.invoice_line_ids:
                b10, i10, b5, i5, ex = self.calcular_impuestos_linea(linea)
                base10 += b10
                iva10 += i10
                base5 += b5
                iva5 += i5
                exentas += ex

            # --- LOGICA DE CONVERSIÓN DINÁMICA ---
            
            # 1. Obtenemos la tasa bonita para imprimir
            tipo_cambio_visual = self.get_tipo_cambio(factura)

            # 2. Determinamos si debemos convertir
            if factura.currency_id == self.env.company.currency_id:
                # Mismas monedas, no tocamos nada
                factor_calculo = 1.0
                operacion = 'ninguna'
            else:
                # Monedas distintas: Calculamos la relación real para saber si multiplicar o dividir
                tasa_cruda = 1.0
                # Buscamos la primera línea con valores para sacar la relación matemática
                for line in factura.line_ids:
                    if line.amount_currency and line.balance:
                        tasa_cruda = abs(line.balance / line.amount_currency)
                        break
                
                # Definimos la operación basada en la relación matemática real
                if tasa_cruda < 1.0:
                    # Caso: Moneda Factura "Débil" -> Moneda Empresa "Fuerte" (Ej: PYG -> USD)
                    # La tasa visual (ej. 6900) es inversa a la real (0.00014).
                    # Para convertir 6.900.000 Gs a 1.000 USD usando 6.900, debemos DIVIDIR.
                    operacion = 'dividir'
                else:
                    # Caso: Moneda Factura "Fuerte" -> Moneda Empresa "Débil" (Ej: USD -> PYG)
                    # La tasa visual (ej. 6900) es directa.
                    # Para convertir 100 USD a 690.000 Gs usando 6.900, debemos MULTIPLICAR.
                    operacion = 'multiplicar'

            # 3. Aplicamos la conversión a los montos
            if operacion == 'dividir':
                # Usamos la tasa visual para dividir
                base10 /= tipo_cambio_visual
                iva10 /= tipo_cambio_visual
                base5 /= tipo_cambio_visual
                iva5 /= tipo_cambio_visual
                exentas /= tipo_cambio_visual
            
            elif operacion == 'multiplicar':
                base10 *= tipo_cambio_visual
                iva10 *= tipo_cambio_visual
                base5 *= tipo_cambio_visual
                iva5 *= tipo_cambio_visual
                exentas *= tipo_cambio_visual

            total_factura = base10 + iva10 + base5 + iva5 + exentas
            credito_fiscal = iva10 + iva5

            # --- ESCRITURA ---
            sheet.write(row, 0, contador)
            sheet.write(row, 1, factura.invoice_date, fecha_format)
            sheet.write(row, 2, self.get_tipo_comprobante(factura))
            sheet.write(row, 3, factura.l10n_latam_document_type_id.name if factura.l10n_latam_document_type_id else '')
            sheet.write(row, 4, factura.ref or factura.name)
            sheet.write(row, 5, factura.partner_id.name or '')
            sheet.write(row, 6, factura.partner_id.vat or '')
            sheet.write(row, 7, self.get_condicion_pago(factura))
            sheet.write(row, 8, factura.currency_id.name)
            tc_a_mostrar = tipo_cambio_visual if factura.currency_id.name != company_currency.name else company_currency._convert(1.0, pyg_currency, self.env.company, factura.invoice_date)
            sheet.write(row, 9, tc_a_mostrar, numerico_tc)
            sheet.write(row, 10, base10, numerico_montos)
            sheet.write(row, 11, iva10, numerico_montos)
            sheet.write(row, 12, base5, numerico_montos)
            sheet.write(row, 13, iva5, numerico_montos)
            sheet.write(row, 14, exentas, numerico_montos)
            sheet.write(row, 15, total_factura, numerico_montos)
            sheet.write(row, 16, credito_fiscal, numerico_montos)

            # Acumular
            totales['base10'] += base10
            totales['iva10'] += iva10
            totales['base5'] += base5
            totales['iva5'] += iva5
            totales['exentas'] += exentas
            totales['total'] += total_factura
            totales['credito_fiscal'] += credito_fiscal

            contador += 1
            row += 1

        # --- PROCESAR NOTAS DE CRÉDITO ---
        for nota in notas_credito.sorted(lambda m: (m.invoice_date, m.name)):
            base10, iva10, base5, iva5, exentas = 0, 0, 0, 0, 0
            
            for linea in nota.invoice_line_ids:
                b10, i10, b5, i5, ex = self.calcular_impuestos_linea(linea)
                base10 += b10
                iva10 += i10
                base5 += b5
                iva5 += i5
                exentas += ex

            # Conversión (Misma lógica)
            tipo_cambio_visual = self.get_tipo_cambio(nota)
            
            if nota.currency_id.name == company_currency.name:
                factor_calculo = 1.0
            else:
                factor_calculo = tipo_cambio_visual

            if factor_calculo != 1.0:
                moneda_empresa = company_currency.name
                moneda_factura = nota.currency_id.name

                if moneda_empresa == 'USD' and moneda_factura == 'PYG':
                    base10 /= factor_calculo
                    iva10 /= factor_calculo
                    base5 /= factor_calculo
                    iva5 /= factor_calculo
                    exentas /= factor_calculo
                else:
                    base10 *= factor_calculo
                    iva10 *= factor_calculo
                    base5 *= factor_calculo
                    iva5 *= factor_calculo
                    exentas *= factor_calculo

            total_factura = base10 + iva10 + base5 + iva5 + exentas
            credito_fiscal = iva10 + iva5

            # Escritura (Valores Negativos visuales)
            sheet.write(row, 0, contador)
            sheet.write(row, 1, nota.invoice_date, fecha_format)
            sheet.write(row, 2, self.get_tipo_comprobante(nota))
            sheet.write(row, 3, nota.l10n_latam_document_type_id.name if nota.l10n_latam_document_type_id else '')
            sheet.write(row, 4, nota.invoice_number or nota.name or nota.ref)  
            sheet.write(row, 5, nota.partner_id.name or '')
            sheet.write(row, 6, nota.partner_id.vat or '')
            sheet.write(row, 7, self.get_condicion_pago(nota))            
            sheet.write(row, 8, nota.currency_id.name)
            tc_a_mostrar = tipo_cambio_visual if nota.currency_id.name != company_currency.name else company_currency._convert(1.0, pyg_currency, self.env.company, nota.invoice_date)
            sheet.write(row, 9, tc_a_mostrar, numerico_tc)
            sheet.write(row, 10, -base10, numerico_montos)
            sheet.write(row, 11, -iva10, numerico_montos)
            sheet.write(row, 12, -base5, numerico_montos)
            sheet.write(row, 13, -iva5, numerico_montos)
            sheet.write(row, 14, -exentas, numerico_montos)
            sheet.write(row, 15, -total_factura, numerico_montos)
            sheet.write(row, 16, -credito_fiscal, numerico_montos)

            # Acumular restando
            totales['base10'] -= base10
            totales['iva10'] -= iva10
            totales['base5'] -= base5
            totales['iva5'] -= iva5
            totales['exentas'] -= exentas
            totales['total'] -= total_factura
            totales['credito_fiscal'] -= credito_fiscal

            contador += 1
            row += 1

        # Línea de totales
        row += 1
        sheet.write(row, 0, "TOTALES", bold)
        sheet.write(row, 10, totales['base10'], numerico_total)
        sheet.write(row, 11, totales['iva10'], numerico_total)
        sheet.write(row, 12, totales['base5'], numerico_total)
        sheet.write(row, 13, totales['iva5'], numerico_total)
        sheet.write(row, 14, totales['exentas'], numerico_total)
        sheet.write(row, 15, totales['total'], numerico_total)
        sheet.write(row, 16, totales['credito_fiscal'], numerico_total)


class WizardReporteVenta(models.TransientModel):
    _name = 'reporte_compraventa.wizardventa'
    _description = 'Asistente para Reporte de Ventas'

    fecha_inicio = fields.Date(string='Fecha Inicio', required=True)
    fecha_fin = fields.Date(string='Fecha Fin', required=True)

    def print_report_xlsx(self):
        """Generar reporte Excel de ventas usando controlador personalizado"""
        self.ensure_one()
        
        # Usar controlador personalizado para generar Excel (patrón Odoo 18)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/reporte_compraventa/ventas/xlsx/{self.id}',
            'target': 'new',
        }


class ReporteVentasXLSX(models.AbstractModel):
    _name = 'report.reporte_compraventa.reporte_venta_xlsx'
    _description = 'Reporte de Ventas en formato XLSX'
    _inherit = 'report.report_xlsx.abstract'

    def get_facturas_libro_venta(self, fecha_inicio, fecha_fin):
        """Obtiene las facturas de venta publicadas en el período"""
        return self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_number', '!=', False),
            ('invoice_date', '>=', fecha_inicio),
            ('invoice_date', '<=', fecha_fin),
            ('company_id', '=', self.env.company.id),
        ])

    def get_notas_credito_venta(self, fecha_inicio, fecha_fin):
        """Obtiene las notas de crédito de venta publicadas en el período"""
        return self.env['account.move'].search([
            ('move_type', '=', 'out_refund'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', fecha_inicio),
            ('invoice_date', '<=', fecha_fin),
            ('company_id', '=', self.env.company.id),
        ])

    def calcular_impuestos_linea(self, invoice_line):
        """Calcula los impuestos para una línea de factura"""
        base10 = 0
        iva10 = 0
        base5 = 0
        iva5 = 0
        exentas = 0
        
        if invoice_line.tax_ids:
            for tax in invoice_line.tax_ids:
                if tax.amount == 10:
                    base10 += invoice_line.price_subtotal
                    iva10 += invoice_line.price_subtotal * 0.10
                elif tax.amount == 5:
                    base5 += invoice_line.price_subtotal
                    iva5 += invoice_line.price_subtotal * 0.05
                elif tax.amount == 0:
                    exentas += invoice_line.price_subtotal
        else:
            # Si no hay impuestos, se considera exenta
            exentas += invoice_line.price_subtotal

        return base10, iva10, base5, iva5, exentas

    def get_tipo_comprobante(self, move):
        """Determina el tipo de comprobante"""
        if move.move_type == 'out_invoice':
            return 'Factura'
        elif move.move_type == 'out_refund':
            return 'Nota de Crédito'
        elif move.move_type == 'out_debit':
            return 'Nota de Débito'
        else:
            return 'Otro'

    def get_condicion_pago(self, move):
        """Determina si es contado o crédito"""
        if move.invoice_date and move.invoice_date_due:
            if move.invoice_date < move.invoice_date_due:
                return 'Crédito'
            else:
                return 'Contado'
        return 'Contado'

    def get_tipo_cambio(self, move):
        """
        Obtiene el tipo de cambio de forma legible (ej. 6900 en lugar de 0.00014).
        Funciona para:
        - Empresa PYG / Factura USD
        - Empresa USD / Factura PYG
        """
        # 1. Si las monedas son iguales, el cambio es 1.0
        if move.currency_id == self.env.company.currency_id:
            return 1.0

        for line in move.line_ids:
            # Buscamos una línea que tenga montos para poder calcular
            if line.amount_currency and line.balance:
                
                # 2. Calculamos el factor crudo de Odoo
                tasa_calculada = abs(line.balance / line.amount_currency)
                
                # 3. Lógica de inversión inteligente:
                # Si la tasa es muy pequeña (ej: 0.000145), significa que estamos 
                # convirtiendo de Moneda Débil (PYG) a Fuerte (USD).
                # Para verlo "humano" (6880), invertimos la división.
                if tasa_calculada < 1.0 and tasa_calculada > 0:
                    return 1.0 / tasa_calculada
                
                # Si la tasa es grande (ej: 6880), significa que es USD -> PYG. 
                # Ya está en el formato correcto.
                return tasa_calculada
                
        return 1.0

    def generate_xlsx_report(self, workbook, data, datas):
        """Genera el reporte XLSX de ventas"""
        # definimos la moneda PYG
        pyg_currency = self.env['res.currency'].search([('name', '=', 'PYG')], limit=1)
        
        # 1. Determinar el formato de moneda base (Moneda de la Compañía)
        company_currency = self.env.company.currency_id
        
        # Construcción dinámica basada en decimal_places
        n_decimals = company_currency.decimal_places
        decimal_part = '.' + ('0' * n_decimals) if n_decimals > 0 else ''
        str_format_montos = f'#,##0{decimal_part}'
        
        # Configuración de formatos
        bold = workbook.add_format({'bold': True})
        
        # Formato para los Montos (Dinámico)
        numerico_montos = workbook.add_format({'num_format': str_format_montos, 'align': 'right'})
        numerico_total = workbook.add_format({'num_format': str_format_montos, 'align': 'right', 'bold': True})
        
        # Formato para el Tipo de Cambio (Siempre con decimales)
        numerico_tc = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        
        wrapped_text = workbook.add_format({'text_wrap': True})
        wrapped_text_bold = workbook.add_format({'text_wrap': True, 'bold': True})
        fecha_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
        # Crear hoja de trabajo
        sheet = workbook.add_worksheet('Libro IVA Ventas')
        
        # Configurar ancho de columnas (Ajustado para nueva columna)
        sheet.set_column('A:A', 8)   # Nro
        sheet.set_column('B:B', 12)  # Fecha
        sheet.set_column('C:C', 15)  # Tipo
        sheet.set_column('D:D', 15)  # Estado del DE
        sheet.set_column('E:E', 15)  # Timbrado
        sheet.set_column('F:F', 20)  # Número
        sheet.set_column('G:G', 30)  # Cliente
        sheet.set_column('H:H', 15)  # RUC
        sheet.set_column('I:I', 10)  # Condición
        sheet.set_column('J:J', 8)   # Moneda
        sheet.set_column('K:K', 10)  # T.C.
        sheet.set_column('L:L', 15)  # Base 10%
        sheet.set_column('M:M', 12)  # IVA 10%
        sheet.set_column('N:N', 15)  # Base 5%
        sheet.set_column('O:O', 12)  # IVA 5%
        sheet.set_column('P:P', 12)  # Exentas
        sheet.set_column('Q:Q', 15)  # Total
        sheet.set_column('R:R', 15)  # Débito Fiscal

        # Encabezado del reporte
        row = 0
        sheet.write(row, 0, "Razón social:", bold)
        sheet.write(row, 1, self.env.company.name)
        row += 1
        sheet.write(row, 0, "RUC:", bold)
        sheet.write(row, 1, self.env.company.partner_id.vat or '')
        row += 1
        sheet.write(row, 0, "Período:", bold)
        sheet.write(row, 1, f"Del {datas.fecha_inicio.strftime('%d/%m/%Y')} al {datas.fecha_fin.strftime('%d/%m/%Y')}")
        row += 2

        sheet.write(row, 0, "LIBRO IVA VENTAS - LEY 125/91", bold)
        row += 1

        # Encabezados de columnas
        headers = [
            "Nro", "Fecha", "Tipo", "Estado del DE", "Timbrado/Est/Pto", "Número", "Cliente", 
            "RUC", "Condición", "Moneda", "T.C.", "Base 10%", "IVA 10%", 
            "Base 5%", "IVA 5%", "Exentas", "Total", "Débito Fiscal"
        ]
        
        for col, header in enumerate(headers):
            sheet.write(row, col, header, wrapped_text_bold)
        row += 1

        facturas = self.get_facturas_libro_venta(datas.fecha_inicio, datas.fecha_fin)
        notas_credito = self.get_notas_credito_venta(datas.fecha_inicio, datas.fecha_fin)
        
        totales = {
            'base10': 0, 'iva10': 0, 'base5': 0, 'iva5': 0, 
            'exentas': 0, 'total': 0, 'debito_fiscal': 0
        }

        # --- PROCESAR FACTURAS ---
        contador = 1
        # Usamos sorted para ordenar cronológicamente
        for factura in facturas.sorted(lambda m: (m.invoice_date, m.name)):
            base10, iva10, base5, iva5, exentas = 0, 0, 0, 0, 0
            
            for linea in factura.invoice_line_ids:
                b10, i10, b5, i5, ex = self.calcular_impuestos_linea(linea)
                base10 += b10
                iva10 += i10
                base5 += b5
                iva5 += i5
                exentas += ex

            # --- LOGICA DE CONVERSIÓN DINÁMICA ---
            
            # 1. Obtenemos la tasa bonita para imprimir
            tipo_cambio_visual = self.get_tipo_cambio(factura)

            # 2. Determinamos si debemos convertir
            if factura.currency_id == self.env.company.currency_id:
                # Mismas monedas, no tocamos nada
                factor_calculo = 1.0
                operacion = 'ninguna'
            else:
                # Monedas distintas: Calculamos la relación real para saber si multiplicar o dividir
                tasa_cruda = 1.0
                # Buscamos la primera línea con valores para sacar la relación matemática
                for line in factura.line_ids:
                    if line.amount_currency and line.balance:
                        tasa_cruda = abs(line.balance / line.amount_currency)
                        break
                
                # Definimos la operación basada en la relación matemática real
                if tasa_cruda < 1.0:
                    # Caso: Moneda Factura "Débil" -> Moneda Empresa "Fuerte" (Ej: PYG -> USD)
                    # La tasa visual (ej. 6900) es inversa a la real (0.00014).
                    # Para convertir 6.900.000 Gs a 1.000 USD usando 6.900, debemos DIVIDIR.
                    operacion = 'dividir'
                else:
                    # Caso: Moneda Factura "Fuerte" -> Moneda Empresa "Débil" (Ej: USD -> PYG)
                    # La tasa visual (ej. 6900) es directa.
                    # Para convertir 100 USD a 690.000 Gs usando 6.900, debemos MULTIPLICAR.
                    operacion = 'multiplicar'

            # 3. Aplicamos la conversión a los montos
            if operacion == 'dividir':
                # Usamos la tasa visual para dividir
                base10 /= tipo_cambio_visual
                iva10 /= tipo_cambio_visual
                base5 /= tipo_cambio_visual
                iva5 /= tipo_cambio_visual
                exentas /= tipo_cambio_visual
            
            elif operacion == 'multiplicar':
                base10 *= tipo_cambio_visual
                iva10 *= tipo_cambio_visual
                base5 *= tipo_cambio_visual
                iva5 *= tipo_cambio_visual
                exentas *= tipo_cambio_visual

            total_factura = base10 + iva10 + base5 + iva5 + exentas
            debito_fiscal = iva10 + iva5

            # --- ESCRITURA EN EXCEL ---
            estado_de = ''
            if hasattr(factura, 'de_status') and factura.de_status:
                f_field = factura._fields.get('de_status')
                if f_field and f_field.type == 'selection':
                    estado_de = dict(f_field._description_selection(self.env)).get(factura.de_status, factura.de_status)
                else:
                    estado_de = factura.de_status

            sheet.write(row, 0, contador)
            sheet.write(row, 1, factura.invoice_date, fecha_format)
            sheet.write(row, 2, self.get_tipo_comprobante(factura))
            sheet.write(row, 3, estado_de)
            sheet.write(row, 4, factura.authorization_id.stamped or '')
            sheet.write(row, 5, factura.invoice_number or factura.name)
            sheet.write(row, 6, factura.partner_id.name or '')
            sheet.write(row, 7, factura.partner_id.vat or '')
            sheet.write(row, 8, self.get_condicion_pago(factura))
            sheet.write(row, 9, factura.currency_id.name) 
            tc_a_mostrar = tipo_cambio_visual if factura.currency_id.name != company_currency.name else company_currency._convert(1.0, pyg_currency, self.env.company, factura.invoice_date)
            sheet.write(row, 10, tc_a_mostrar, numerico_tc)

            # Columnas de Montos (Usan numerico_montos dinámico)
            sheet.write(row, 11, base10, numerico_montos)
            sheet.write(row, 12, iva10, numerico_montos)
            sheet.write(row, 13, base5, numerico_montos)
            sheet.write(row, 14, iva5, numerico_montos)
            sheet.write(row, 15, exentas, numerico_montos)
            sheet.write(row, 16, total_factura, numerico_montos)
            sheet.write(row, 17, debito_fiscal, numerico_montos)

            # Acumular totales
            totales['base10'] += base10
            totales['iva10'] += iva10
            totales['base5'] += base5
            totales['iva5'] += iva5
            totales['exentas'] += exentas
            totales['total'] += total_factura
            totales['debito_fiscal'] += debito_fiscal

            contador += 1
            row += 1

        # --- PROCESAR NOTAS DE CRÉDITO ---
        for nota in notas_credito.sorted(lambda m: (m.invoice_date, m.name)):
            base10, iva10, base5, iva5, exentas = 0, 0, 0, 0, 0
            
            for linea in nota.invoice_line_ids:
                b10, i10, b5, i5, ex = self.calcular_impuestos_linea(linea)
                base10 += b10
                iva10 += i10
                base5 += b5
                iva5 += i5
                exentas += ex

            # Conversión (Misma lógica)
            tipo_cambio_visual = self.get_tipo_cambio(nota)
            
            if nota.currency_id.name == company_currency.name:
                factor_calculo = 1.0
            else:
                factor_calculo = tipo_cambio_visual

            if factor_calculo != 1.0:
                moneda_empresa = company_currency.name
                moneda_factura = nota.currency_id.name

                if moneda_empresa == 'USD' and moneda_factura == 'PYG':
                    base10 /= factor_calculo
                    iva10 /= factor_calculo
                    base5 /= factor_calculo
                    iva5 /= factor_calculo
                    exentas /= factor_calculo
                else:
                    base10 *= factor_calculo
                    iva10 *= factor_calculo
                    base5 *= factor_calculo
                    iva5 *= factor_calculo
                    exentas *= factor_calculo

            total_factura = base10 + iva10 + base5 + iva5 + exentas
            debito_fiscal = iva10 + iva5

            # Escritura (Valores Negativos visuales)
            estado_de_nc = ''
            if hasattr(nota, 'de_status') and nota.de_status:
                f_field = nota._fields.get('de_status')
                if f_field and f_field.type == 'selection':
                    estado_de_nc = dict(f_field._description_selection(self.env)).get(nota.de_status, nota.de_status)
                else:
                    estado_de_nc = nota.de_status

            sheet.write(row, 0, contador)
            sheet.write(row, 1, nota.invoice_date, fecha_format)
            sheet.write(row, 2, self.get_tipo_comprobante(nota))
            sheet.write(row, 3, estado_de_nc)
            sheet.write(row, 4, nota.authorization_id.stamped if hasattr(nota, 'authorization_id') and nota.authorization_id else '')
            sheet.write(row, 5, nota.invoice_number or nota.name or nota.ref)
            sheet.write(row, 6, nota.partner_id.name or '')
            sheet.write(row, 7, nota.partner_id.vat or '')
            sheet.write(row, 8, self.get_condicion_pago(nota))
            sheet.write(row, 9, nota.currency_id.name)
            tc_a_mostrar = tipo_cambio_visual if nota.currency_id.name != company_currency.name else company_currency._convert(1.0, pyg_currency, self.env.company, nota.invoice_date)
            sheet.write(row, 10, tc_a_mostrar, numerico_tc)
            sheet.write(row, 11, -base10, numerico_montos)
            sheet.write(row, 12, -iva10, numerico_montos)
            sheet.write(row, 13, -base5, numerico_montos)
            sheet.write(row, 14, -iva5, numerico_montos)
            sheet.write(row, 15, -exentas, numerico_montos)
            sheet.write(row, 16, -total_factura, numerico_montos)
            sheet.write(row, 17, -debito_fiscal, numerico_montos)

            # Acumular restando
            totales['base10'] -= base10
            totales['iva10'] -= iva10
            totales['base5'] -= base5
            totales['iva5'] -= iva5
            totales['exentas'] -= exentas
            totales['total'] -= total_factura
            totales['debito_fiscal'] -= debito_fiscal

            contador += 1
            row += 1

        # --- TOTALES ---
        row += 1
        sheet.write(row, 0, "TOTALES", bold)
        sheet.write(row, 11, totales['base10'], numerico_total)
        sheet.write(row, 12, totales['iva10'], numerico_total)
        sheet.write(row, 13, totales['base5'], numerico_total)
        sheet.write(row, 14, totales['iva5'], numerico_total)
        sheet.write(row, 15, totales['exentas'], numerico_total)
        sheet.write(row, 16, totales['total'], numerico_total)
        sheet.write(row, 17, totales['debito_fiscal'], numerico_total)
