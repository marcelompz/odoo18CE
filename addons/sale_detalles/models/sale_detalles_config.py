from odoo import models, fields, api
from datetime import datetime, timedelta

SEQUENCE_PRODUCT_CODE = 'sale_detalles.product.product'


class SaleDetallesConfig(models.Model):
    _name = 'sale.detalles.config'
    _description = 'Configuración de Sale Detalles'
    _rec_name = 'name'

    name = fields.Char(string='Nombre de Configuración', default='Configuración Principal', required=True)
    min_validity_date_days = fields.Integer(
        string='Días Mínimos para Validity Date',
        default=1,
        help='Número mínimo de días que debe tener la validity_date desde hoy para poder aprobar la venta'
    )
    active = fields.Boolean(string='Activo', default=True)
    
    # Secuencia de productos: siguiente número a usar
    sequence_product_next_number = fields.Integer(
        string='Siguiente Nº de Producto',
        compute='_compute_sequence_product_next_number',
        inverse='_inverse_sequence_product_next_number',
        help='Próximo número a usar en la secuencia de códigos de producto (ej: MER/0001)'
    )

    # Campo calculado para mostrar la fecha mínima real
    min_validity_date = fields.Date(
        string='Fecha Mínima Calculada',
        compute='_compute_min_validity_date',
        store=False,
        help='Fecha mínima calculada basada en los días configurados'
    )
    
    @api.depends('min_validity_date_days')
    def _compute_min_validity_date(self):
        """Calcula la fecha mínima de validity_date basada en la configuración"""
        for record in self:
            if record.min_validity_date_days:
                record.min_validity_date = fields.Date.today() + timedelta(days=record.min_validity_date_days)
            else:
                record.min_validity_date = False
    
    def _get_product_sequence(self):
        return self.env['ir.sequence'].search([('code', '=', SEQUENCE_PRODUCT_CODE)], limit=1)

    @api.depends()
    def _compute_sequence_product_next_number(self):
        for record in self:
            seq = record._get_product_sequence()
            record.sequence_product_next_number = seq.number_next_actual if seq else 1

    def _inverse_sequence_product_next_number(self):
        seq = self._get_product_sequence()
        if seq:
            for record in self:
                if record.sequence_product_next_number >= 1:
                    seq.number_next_actual = record.sequence_product_next_number
                    break  # Solo actualizar una vez (la secuencia es global)

    @api.model
    def get_min_validity_date(self):
        """Obtiene la fecha mínima de validity_date basada en la configuración"""
        config = self.search([('active', '=', True)], limit=1)
        if config:
            return datetime.now().date() + timedelta(days=config.min_validity_date_days)
        return datetime.now().date() + timedelta(days=1)  # Valor por defecto
    
    @api.model
    def check_validity_date_approval(self, validity_date):
        """Verifica si una validity_date es válida para aprobar la venta"""
        if not validity_date:
            return False, 'La fecha de vencimiento es obligatoria'
        
        min_date = self.get_min_validity_date()
        if validity_date < min_date:
            return False, f'La fecha de vencimiento debe ser al menos {min_date.strftime("%d/%m/%Y")}'
        
        return True, 'Fecha de vencimiento válida' 