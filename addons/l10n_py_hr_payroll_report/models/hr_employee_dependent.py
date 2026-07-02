# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class HrEmployeeDependent(models.Model):
    _name = 'hr.employee.dependent'
    _description = 'Dependientes del Empleado'
    _order = 'birth_date desc'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    name = fields.Char(string='Nombre Completo', required=True)
    identification_id = fields.Char(string='C.I. N°', help='Cédula de Identidad del dependiente')
    birth_date = fields.Date(string='Fecha de Nacimiento', required=True)
    relationship = fields.Selection([
        ('hijo', 'Hijo/a'),
        ('hijastro', 'Hijastro/a'),
        ('otro', 'Otro'),
    ], string='Parentesco', default='hijo', required=True)
    is_student = fields.Boolean(string='Es Estudiante', help='Si el dependiente es estudiante, puede extender la edad de dependencia hasta 24 años')
    is_active = fields.Boolean(string='Activo', default=True, help='Indica si el dependiente está activo')
    
    # Campos calculados
    age = fields.Integer(string='Edad', compute='_compute_age', store=False)
    is_dependent = fields.Boolean(string='Es Dependiente', compute='_compute_is_dependent', store=False, help='Calcula si el dependiente tiene derecho a bonificación familiar según su edad')

    @api.depends('birth_date')
    def _compute_age(self):
        """Calcular edad del dependiente"""
        today = date.today()
        for record in self:
            if record.birth_date:
                age = today.year - record.birth_date.year
                if today.month < record.birth_date.month or (today.month == record.birth_date.month and today.day < record.birth_date.day):
                    age -= 1
                record.age = age
            else:
                record.age = 0

    @api.depends('birth_date', 'is_student', 'is_active')
    def _compute_is_dependent(self):
        """Determinar si es dependiente según edad"""
        today = date.today()
        
        for record in self:
            if not record.birth_date or not record.is_active:
                record.is_dependent = False
                continue
            
            max_age = 24 if record.is_student else 18
            age = today.year - record.birth_date.year
            if today.month < record.birth_date.month or (today.month == record.birth_date.month and today.day < record.birth_date.day):
                age -= 1
            
            # Es dependiente si tiene menos de la edad máxima
            record.is_dependent = age < max_age

