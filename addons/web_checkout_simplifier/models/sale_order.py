from odoo import models, fields, api
import base64


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    checkout_attachment = fields.Binary(
        string='Archivo de Checkout',
        help='Archivo subido durante el proceso de checkout'
    )
    checkout_attachment_name = fields.Char(
        string='Nombre del Archivo',
        help='Nombre del archivo subido durante el checkout'
    )

    def _process_checkout_attachment(self, file_data, filename):
        """
        Procesa el archivo subido durante el checkout y lo guarda como comentario
        """
        if file_data and filename:
            # Guardar el archivo como attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': file_data,
                'res_model': 'sale.order',
                'res_id': self.id,
                'type': 'binary',
            })
            
            # Agregar comentario a la orden
            comment = f"Archivo adjunto subido durante el checkout: {filename}"
            if self.note:
                self.note = f"{self.note}\n\n{comment}"
            else:
                self.note = comment
                
            # Guardar referencia del archivo en los campos específicos
            self.checkout_attachment = file_data
            self.checkout_attachment_name = filename
            
            return attachment
        return False

    @api.model
    def create(self, vals):
        """
        Override create para procesar archivos adjuntos durante la creación
        """
        order = super(SaleOrder, self).create(vals)
        
        # Procesar archivo adjunto si existe
        if vals.get('checkout_attachment') and vals.get('checkout_attachment_name'):
            order._process_checkout_attachment(
                vals['checkout_attachment'],
                vals['checkout_attachment_name']
            )
        
        return order

    def write(self, vals):
        """
        Override write para procesar archivos adjuntos durante la actualización
        """
        result = super(SaleOrder, self).write(vals)
        
        # Procesar archivo adjunto si existe
        if vals.get('checkout_attachment') and vals.get('checkout_attachment_name'):
            for order in self:
                order._process_checkout_attachment(
                    vals['checkout_attachment'],
                    vals['checkout_attachment_name']
                )
        
        return result

