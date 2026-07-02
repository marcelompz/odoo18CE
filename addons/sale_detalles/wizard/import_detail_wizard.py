from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ImportDetailWizard(models.TransientModel):
    _name = 'import.detail.wizard'
    _description = 'Asistente para importar detalles'

    order_id = fields.Many2one('sale.order', string='Orden de venta', required=True)
    order_name = fields.Char(related='order_id.name', string='Número de orden')
    import_data = fields.Text('Datos a importar')

    @api.model
    def default_get(self, fields_list):
        res = super(ImportDetailWizard, self).default_get(fields_list)
        # Obtener order_id del contexto si está disponible
        if 'order_id' in fields_list and not res.get('order_id'):
            # Intentar obtener desde default_order_id primero
            default_order_id = self._context.get('default_order_id')
            if default_order_id:
                res['order_id'] = default_order_id
            else:
                # Intentar obtener desde active_id y active_model
                active_id = self._context.get('active_id')
                active_model = self._context.get('active_model')
                if active_model == 'sale.order' and active_id:
                    res['order_id'] = active_id
        return res

    def action_import(self):
        if not self.order_id:
            raise UserError('Debe seleccionar una orden de venta antes de importar.')
        
        # Validar que la orden tenga una plantilla de cotización asignada
        if not self.order_id.sale_order_template_id:
            raise UserError('La orden de venta debe tener una plantilla de cotización asignada.')
        
        # Obtener el código de la plantilla
        template_code = self.order_id.sale_order_template_id.code
        if not template_code:
            raise UserError('La plantilla de cotización asignada no tiene código. Por favor, asigne un código a la plantilla.')
        
        if not self.import_data:
            raise UserError('Debe ingresar datos en el campo de importación.')
        
        lines = self.import_data.strip().split('\n')
        if len(lines) < 2:
            raise UserError('No hay datos para importar (debe incluir encabezados y al menos una fila de datos).')
        
        headers = lines[0].split('\t')
        # Normalizar encabezados a minúsculas para acceso insensible a mayúsculas
        headers_lower = [h.lower().strip() for h in headers]
        errores = []
        
        for row_num, row in enumerate(lines[1:], start=2):
            if not row.strip():
                continue
            
            values = row.split('\t')
            # Asegurar que tenemos suficientes valores
            while len(values) < len(headers_lower):
                values.append('')
            
            data = dict(zip(headers_lower, values))
            
            # Buscar el modelo por nombre
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
                'name_customer': data.get('nombre', '').strip(),
                'number_customer': data.get('numero', '').strip(),
                'other_customer': data.get('otros', '').strip(),
                'quantity': float(data.get('cantidad', 1) or 1),
            }
            
            # Procesar categorías (categoría1-talle1, categoría2-talle2, etc.)
            for i in range(1, 6):
                # Intentar primero con tilde, luego sin tilde para compatibilidad
                categoria_key = f'categoría{i}'
                if categoria_key not in data:
                    categoria_key = f'categoria{i}'
                talle_key = f'talle{i}'
                categoria_nombre = data.get(categoria_key, '').strip()
                talle = data.get(talle_key, '').strip()
                
                if categoria_nombre or talle:
                    if not categoria_nombre:
                        errores.append(f"Fila {row_num}: Falta el nombre de la categoría en {categoria_key}.")
                        continue
                    if not talle:
                        errores.append(f"Fila {row_num}: Falta la talla en {talle_key} para la categoría '{categoria_nombre}'.")
                        continue
                    
                    # Buscar la categoría por nombre
                    categoria_obj = self.env['product.category'].search([('name', '=', categoria_nombre)], limit=1)
                    if not categoria_obj:
                        errores.append(f"Fila {row_num}: No se encontró la categoría con nombre '{categoria_nombre}'.")
                        continue
                    
                    # Validar que la categoría tenga código
                    if not categoria_obj.code:
                        errores.append(f"Fila {row_num}: La categoría '{categoria_nombre}' no tiene código asignado.")
                        continue
                    
                    # Construir código final: código_plantilla-código_categoría-talle
                    codigo_final = f"{template_code}-{categoria_obj.code}-{talle}"
                    product = self.env['product.product'].search([('default_code', '=', codigo_final)], limit=1)
                    
                    if not product:
                        errores.append(f"Fila {row_num}: No se encontró el producto con código '{codigo_final}'.")
                        continue
                    
                    vals[f'product{i}_variant_id'] = product.id
            
            # Crear la línea de detalle
            try:
                self.env['order.detail.lines'].create(vals)
            except Exception as e:
                errores.append(f"Fila {row_num}: Error al crear la línea de detalle: {str(e)}")
        
        if errores:
            raise UserError('Errores encontrados en la importación:\n' + '\n'.join(errores))
        
        return {'type': 'ir.actions.act_window_close'}
    