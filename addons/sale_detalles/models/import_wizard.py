from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import xlsxwriter
from io import BytesIO

class ImportDetailWizard(models.TransientModel):
    _name = 'import.detail.wizard'
    _description = 'Wizard para importar detalles de órdenes'

    order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True)
    order_name = fields.Char(related='order_id.name', string='Número de Orden', readonly=True)
    model_line_id = fields.Many2one('order.detail.model.lines', string='Modelo', 
                                     domain="[('order_id', '=', order_id)]",
                                     help='Seleccione un modelo para precargar sus productos relacionados')
    import_data = fields.Text(string='Datos a Importar')
    product_reference_ids = fields.One2many('import.detail.wizard.line', 'wizard_id', string='Productos y Referencias')
    template_file = fields.Binary(string='Plantilla Excel', readonly=True)
    template_filename = fields.Char(string='Nombre del archivo', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ImportDetailWizard, self).default_get(fields_list)
        order = None
        if res.get('order_id'):
            order = self.env['sale.order'].browse(res['order_id'])
        elif self._context.get('active_id'):
            order = self.env['sale.order'].browse(self._context['active_id'])
            res['order_id'] = order.id
        if order:
            res['template_filename'] = f'Plantilla_Importacion_{order.name}.xlsx'
            res['template_file'] = self._create_template()
        return res

    def _create_template(self):
        # Crear archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Plantilla')

        # Definir formatos
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#D3D3D3',
            'border': 1
        })

        # Escribir encabezados
        headers = ['Modelo', 'nombre', 'numero', 'otros', 'cantidad',
                  'producto1', 'talle1', 'producto2', 'talle2',
                  'producto3', 'talle3', 'producto4', 'talle4',
                  'producto5', 'talle5']
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 15)  # Ancho de columna

        # Agregar ejemplo
        example = ['Modelo1', 'Juan', '123', 'Nota', '1',
                  'REF1', 'S', 'REF2', 'M', '', '', '', '', '', '']
        for col, value in enumerate(example):
            worksheet.write(1, col, value)

        workbook.close()
        return base64.b64encode(output.getvalue())

    def action_import(self):
        if not self.order_id:
            raise UserError('Debe seleccionar una orden de venta antes de importar.')
        name_to_code = {line.reference.strip(): line.product_id.default_code for line in self.product_reference_ids if line.product_id and line.reference}
        if not name_to_code:
            raise UserError('Debe ingresar al menos una referencia de producto en la lista.')
        if not self.import_data:
            raise UserError('Debe ingresar datos en el campo de importación.')

        lines = self.import_data.strip().split('\n')
        headers = lines[0].split('\t')
        # Normalizar encabezados a minúsculas para acceso insensible a mayúsculas
        headers_lower = [h.lower() for h in headers]
        errores = []
        for row_num, row in enumerate(lines[1:], start=2):
            values = row.split('\t')
            data = dict(zip(headers_lower, values))
            # Buscar el modelo por nombre, usando la clave 'modelo' en minúsculas
            modelo_nombre = data.get('modelo', '').strip()
            modelo_obj = self.env['model.type'].search([('name', '=', modelo_nombre)], limit=1)
            if not modelo_obj:
                errores.append(f"Fila {row_num}: No se encontró el modelo con nombre '{modelo_nombre}'.")
                continue
            if not self.order_id.id:
                errores.append(f"Fila {row_num}: No se pudo obtener el ID de la orden de venta.")
                continue
            vals = {
                'order_id': self.order_id.id,
                'customer_model': modelo_obj.id,
                'name_customer': data.get('nombre'),
                'number_customer': data.get('numero'),
                'other_customer': data.get('otros'),
                'quantity': data.get('cantidad') or 1,
            }
            for i in range(1, 6):
                prod_key = f'producto{i}'
                talle_key = f'talle{i}'
                prod_name = data.get(prod_key, '').strip()
                talle = data.get(talle_key, '').strip()
                if prod_name or talle:
                    if not prod_name:
                        errores.append(f"Fila {row_num}: Falta el nombre del producto en {prod_key}.")
                        continue
                    if not talle:
                        errores.append(f"Fila {row_num}: Falta la talla en {talle_key} para el producto '{prod_name}'.")
                        continue
                    prod_code = name_to_code.get(prod_name)
                    if not prod_code:
                        errores.append(f"Fila {row_num}: El producto '{prod_name}' no está en la lista de referencias.")
                        continue
                    codigo_final = f"{prod_code}-{talle}"
                    product = self.env['product.product'].search([('default_code', '=', codigo_final)], limit=1)
                    if not product:
                        errores.append(f"Fila {row_num}: No se encontró el producto con código '{codigo_final}'.")
                        continue
                    vals[f'product{i}_variant_id'] = product.id
            self.env['order.detail.lines'].create(vals)
        if errores:
            raise UserError('Errores encontrados en la importación:\n' + '\n'.join(errores))
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            self.template_filename = f'Plantilla_Importacion_{self.order_id.name}.xlsx'
            self.template_file = self._create_template()
            # Limpiar el modelo cuando cambia la orden
            self.model_line_id = False
            self.product_reference_ids = [(5, 0, 0)]
        else:
            self.template_filename = False
            self.template_file = False
    
    @api.onchange('model_line_id')
    def _onchange_model_line_id(self):
        """Precargar productos relacionados cuando se selecciona un modelo"""
        if self.model_line_id and self.model_line_id.product_ids:
            # Obtener los productos relacionados del modelo
            product_lines = []
            existing_product_ids = self.product_reference_ids.mapped('product_id').ids
            
            for product_template in self.model_line_id.product_ids:
                # Buscar variantes del producto que tengan show_in_import_reference
                product_variants = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('product_tmpl_id.show_in_import_reference', '=', True)
                ])
                
                # Si hay variantes, agregar todas las que no estén ya en la lista
                if product_variants:
                    for variant in product_variants:
                        if variant.id not in existing_product_ids:
                            product_lines.append((0, 0, {
                                'product_id': variant.id,
                                'reference': variant.default_code or variant.name or ''
                            }))
                            existing_product_ids.append(variant.id)
                else:
                    # Si no hay variantes con show_in_import_reference, buscar cualquier variante
                    first_product = self.env['product.product'].search([
                        ('product_tmpl_id', '=', product_template.id)
                    ], limit=1)
                    if first_product and first_product.id not in existing_product_ids:
                        product_lines.append((0, 0, {
                            'product_id': first_product.id,
                            'reference': first_product.default_code or first_product.name or ''
                        }))
                        existing_product_ids.append(first_product.id)
            
            # Agregar las nuevas líneas de productos sin eliminar las existentes
            if product_lines:
                # Crear las nuevas líneas directamente
                for line_vals in product_lines:
                    self.env['import.detail.wizard.line'].create({
                        'wizard_id': self.id,
                        'product_id': line_vals[2]['product_id'],
                        'reference': line_vals[2]['reference']
                    })

class ImportDetailWizardLine(models.TransientModel):
    _name = 'import.detail.wizard.line'
    _description = 'Líneas de productos y referencias del wizard'

    wizard_id = fields.Many2one('import.detail.wizard', string='Wizard', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True, domain="[('product_tmpl_id.show_in_import_reference', '=', True)]")
    reference = fields.Char(string='Referencia', required=True)

    def action_import(self):
        self.ensure_one()
        lines = self.import_data.strip().split('\n')
        
        # Ignorar la primera línea (encabezados)
        if len(lines) < 2:
            raise UserError('No hay datos para importar')
        
        for line in lines[1:]:
            if not line.strip():
                continue
                
            fields = line.split('\t')
            # Rellenar campos faltantes con valores vacíos
            while len(fields) < 15:
                fields.append('')
            
            # Buscar productos por código
            products = []
            for i in range(5):
                product_code = fields[5 + (i*2)].strip()
                price_str = fields[6 + (i*2)].strip()
                
                # Solo procesar si hay código de producto
                if product_code:
                    if not price_str:
                        raise UserError(f'Falta el precio para el producto {product_code} en la línea: {line}')
                    
                    product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
                    if not product:
                        raise UserError(f'Producto no encontrado con código: {product_code}')
                    products.append((product, float(price_str)))
                else:
                    products.append((False, 0.0))

            # Verificar que al menos un producto esté definido
            if not any(p[0] for p in products):
                raise UserError(f'La línea debe tener al menos un producto definido: {line}')

            # Crear línea de detalle
            detail_vals = {
                'order_id': self.order_id.id,
                'customer_model': 'modelo' + fields[0].split()[-1],
                'name_customer': fields[1],
                'number_customer': fields[2],
                'other_customer': fields[3],
                'quantity': float(fields[4]),
                'product1_variant_id': products[0][0].id if products[0][0] else False,
                'product2_variant_id': products[1][0].id if products[1][0] else False,
                'product3_variant_id': products[2][0].id if products[2][0] else False,
                'product4_variant_id': products[3][0].id if products[3][0] else False,
                'product5_variant_id': products[4][0].id if products[4][0] else False,
            }
            
            detail_line = self.env['order.detail.lines'].create(detail_vals)
            
            # Actualizar precios en las líneas de venta
            for i, (product, price) in enumerate(products, 1):
                if product:
                    sale_lines = detail_line.sale_line_ids.filtered(
                        lambda l: l.product_id == product)
                    for sale_line in sale_lines:
                        sale_line.with_context(check_move_validity=False).write({'price_unit': price})

        return {'type': 'ir.actions.act_window_close'} 