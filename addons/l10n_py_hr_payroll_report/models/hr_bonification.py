# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HrBonification(models.Model):
    _name = 'hr.bonification'
    _description = 'Bonificación de Nómina'
    _order = 'date_from desc, name'

    name = fields.Char(string='Concepto', required=True, help='Nombre o concepto de la bonificación')
    date_from = fields.Date(string='Fecha Desde', required=True, help='Fecha de inicio de validez de la bonificación')
    date_to = fields.Date(string='Fecha Hasta', required=True, help='Fecha de fin de validez de la bonificación')
    amount = fields.Float(string='Monto o Porcentaje', required=True, help='Monto fijo o porcentaje a aplicar')
    amount_type = fields.Selection(
        selection=[
            ('fixed', 'Monto Fijo'),
            ('percentage', 'Porcentaje'),
        ],
        string='Tipo de Monto',
        required=True,
        default='fixed',
        help='Selecciona si el monto es fijo o un porcentaje del salario'
    )
    salary_rule_id = fields.Many2one(
        'hr.salary.rule',
        string='Regla Salarial',
        required=False,
        domain=[('code', '=', 'BONIFICACIONES')],
        ondelete='set null',
        help='Regla salarial asociada a esta bonificación. Si se elimina la regla, este campo se pondrá en null.'
    )
    category_id = fields.Many2one(
        'hr.bonification.category',
        string='Categoría',
        required=True,
        help='Categoría de bonificación'
    )
    active = fields.Boolean(string='Activo', default=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar que la fecha hasta sea mayor o igual que la fecha desde"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError('La fecha hasta debe ser mayor o igual que la fecha desde.')

    @api.constrains('amount_type', 'amount')
    def _check_amount(self):
        """Validar que el porcentaje esté entre 0 y 100"""
        for record in self:
            if record.amount_type == 'percentage':
                if record.amount < 0 or record.amount > 100:
                    raise ValidationError('El porcentaje debe estar entre 0 y 100.')

