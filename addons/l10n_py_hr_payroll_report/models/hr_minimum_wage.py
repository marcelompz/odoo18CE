# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import date


class HrMinimumWage(models.Model):
    _name = 'hr.minimum.wage'
    _description = 'Salario Mínimo Vigente'
    _order = 'date_from desc, name'

    name = fields.Char(string='Nombre', required=True, help='Nombre o descripción del salario mínimo (ej: Salario Mínimo 2025)')
    amount = fields.Float(string='Monto', required=True, help='Monto del salario mínimo')
    date_from = fields.Date(string='Fecha Desde', required=True, help='Fecha de inicio de vigencia')
    date_to = fields.Date(string='Fecha Hasta', help='Fecha de fin de vigencia. Si está vacío, significa que está vigente.')
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.ref('base.PYG', raise_if_not_found=False),
        help='Moneda del salario mínimo'
    )
    active = fields.Boolean(string='Activo', default=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar que la fecha hasta sea mayor o igual que la fecha desde"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError('La fecha hasta debe ser mayor o igual que la fecha desde.')

    @api.constrains('date_from', 'date_to', 'active')
    def _check_overlap(self):
        """Validar que no haya solapamientos de fechas entre registros activos"""
        for record in self:
            if not record.active:
                continue
            
            # Buscar otros registros activos con solapamiento de fechas
            domain = [
                ('id', '!=', record.id),
                ('active', '=', True),
            ]
            
            # Si tiene fecha hasta
            if record.date_to:
                domain.extend([
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', record.date_from),
                    ('date_from', '<=', record.date_to),
                ])
            else:
                # Si no tiene fecha hasta, buscar cualquier registro que pueda solapar
                domain.extend([
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', record.date_from),
                ])
            
            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    f'Ya existe un salario mínimo vigente que se solapa con este rango de fechas. '
                    f'Por favor, ajusta las fechas para evitar solapamientos.'
                )

    @api.model
    def get_current_minimum_wage(self, check_date=None):
        """Obtener el salario mínimo vigente en una fecha específica
        
        Args:
            check_date: Fecha a verificar (por defecto: fecha actual)
        
        Returns:
            Recordset con el salario mínimo vigente o vacío si no hay ninguno
        """
        if check_date is None:
            check_date = date.today()
        
        domain = [
            ('active', '=', True),
            ('date_from', '<=', check_date),
            '|',
            ('date_to', '=', False),
            ('date_to', '>=', check_date),
        ]
        
        return self.search(domain, order='date_from desc', limit=1)

