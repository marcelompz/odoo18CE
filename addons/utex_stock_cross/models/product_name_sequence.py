# -*- coding: utf-8 -*-
"""
Created on 2025-06-16 13:41:16

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductNameSequence(models.Model):
    _name = 'product.name.sequence'
    _description = 'Secuencia del nombre del producto'

    sequence = fields.Integer(
        string='Secuencia', default=100, domain=([('')]))
    fields_id = fields.Many2one(
        'ir.model.fields', string='Campos', required=True, ondelete='cascade', domain=[('model_id.model', '=', 'product.template')])

    @api.constrains('fields_id')
    def _check_field_type(self):
        allowed_types = [
            'char', 'text', 'selection', 'many2one', 
            'integer', 'float', 'monetary', 
            'date', 'datetime', 'many2many'
        ]
        
        for record in self:
            if record.fields_id and record.fields_id.ttype not in allowed_types:
                raise ValidationError(
                    f"El campo '{record.fields_id.field_description}' es de tipo '{record.fields_id.ttype}'.\n"
                    "Solo se permiten campos de tipo Texto, Número, Selección, Fecha o Relacionales."
                )
