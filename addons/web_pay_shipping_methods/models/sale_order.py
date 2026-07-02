from odoo import models, fields, api, _
import logging
import base64
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campos para adjuntos de comprobantes de transferencia
    transfer_receipt_attachment = fields.Binary(
        string='Comprobante de Transferencia',
        help='Comprobante de transferencia subido durante el proceso de pago'
    )
    transfer_receipt_name = fields.Char(
        string='Nombre del Comprobante',
        help='Nombre del archivo del comprobante de transferencia'
    )

    def _process_transfer_receipt_attachment(self, file_data, filename):
        """
        Procesa el archivo subido durante el pago y lo guarda como comentario
        """
        if file_data and filename:
            # Guardar el archivo como attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': file_data,
                'res_model': 'sale.order',
                'res_id': self.id,
                'type': 'binary',
                'public': True,
            })
            
            # Agregar comentario a la orden usando message_post (como en payment_proof_attachment)
            user_name = self.env.user.name if self.env.user else "Cliente"
            body = _("Comprobante de transferencia '%s' agregado por %s durante el proceso de pago." % (filename, user_name))
            
            # Publicar mensaje con el adjunto
            self.message_post(
                body=body,
                attachment_ids=[attachment.id]
            )
                
            # Guardar referencia del archivo en los campos específicos
            self.transfer_receipt_attachment = file_data
            self.transfer_receipt_name = filename
            
            return attachment
        return False

    @api.model
    def create(self, vals):
        """
        Override create para procesar archivos adjuntos durante la creación
        """
        order = super(SaleOrder, self).create(vals)
        
        # Procesar archivo adjunto si existe
        if vals.get('transfer_receipt_attachment') and vals.get('transfer_receipt_name'):
            order._process_transfer_receipt_attachment(
                vals['transfer_receipt_attachment'],
                vals['transfer_receipt_name']
            )
        
        return order

    def write(self, vals):
        """
        Override write para procesar archivos adjuntos durante la actualización
        """
        result = super(SaleOrder, self).write(vals)
        
        # Procesar archivo adjunto si existe
        if vals.get('transfer_receipt_attachment') and vals.get('transfer_receipt_name'):
            for order in self:
                order._process_transfer_receipt_attachment(
                    vals['transfer_receipt_attachment'],
                    vals['transfer_receipt_name']
                )
        
        return result
