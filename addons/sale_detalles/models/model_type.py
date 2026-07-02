from odoo import models, fields, api

class ModelType(models.Model):
    _name = 'model.type'
    _description = 'Tipo de Modelo'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'El código debe ser único!')
    ] 