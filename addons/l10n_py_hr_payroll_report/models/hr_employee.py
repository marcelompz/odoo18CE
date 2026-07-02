# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ips_number = fields.Char(string="Número de Asegurado IPS", help="Número de asegurado en el Instituto de Previsión Social")
    first_name = fields.Char(string="Primer Nombre")
    second_name = fields.Char(string="Segundo Nombre")
    first_last_name = fields.Char(string="Primer Apellido")
    second_last_name = fields.Char(string="Segundo Apellido")
    dnit_ruc = fields.Char(string="RUC (DNIT)")
    dnit_dv = fields.Char(string="DV (DNIT)")
    dnit_payment_type = fields.Selection([
        ('bank', 'Banco'),
        ('cash', 'Efectivo'),
        ('other', 'Otro'),
    ], string="Tipo de Pago (DNIT)")
    dnit_employee_type = fields.Char(string="Tipo de Empleado (DNIT)")
    dnit_department = fields.Char(string="Departamento (DNIT)")
    dnit_district = fields.Char(string="Distrito (DNIT)")
    dnit_locality = fields.Char(string="Localidad/Barrio (DNIT)")
    dnit_address = fields.Char(string="Direccion Completa (DNIT)")
    dnit_phone_prefix = fields.Char(string="Prefijo Linea Fija (DNIT)")
    dnit_phone_line = fields.Char(string="Linea Fija (DNIT)")
    dnit_mobile_prefix = fields.Char(string="Prefijo Celular (DNIT)")
    dnit_mobile_line = fields.Char(string="Celular (DNIT)")
    
    # Categorías de bonificaciones aplicables
    bonification_category_ids = fields.Many2many(
        'hr.bonification.category',
        string='Categorías de Bonificaciones',
        help='Selecciona las categorías de bonificaciones que aplican a este empleado'
    )
    
    # Relación con dependientes
    dependent_ids = fields.One2many('hr.employee.dependent', 'employee_id', string='Dependientes')
    dependent_count = fields.Integer(string='Número de Dependientes', compute='_compute_dependent_count', store=False)
    
    # Método para obtener dependientes activos en una fecha
    def get_dependent_count(self, calculation_date=None):
        """Obtener cantidad de dependientes activos en una fecha específica"""
        self.ensure_one()
        if calculation_date is None:
            calculation_date = date.today()
        
        max_age = 24  # Edad máxima para estudiantes
        regular_max_age = 18  # Edad máxima regular
        
        count = 0
        for dependent in self.dependent_ids:
            if not dependent.is_active or not dependent.birth_date:
                continue
            
            age = calculation_date.year - dependent.birth_date.year
            if calculation_date.month < dependent.birth_date.month or \
               (calculation_date.month == dependent.birth_date.month and calculation_date.day < dependent.birth_date.day):
                age -= 1
            
            # Verificar si es dependiente según su edad
            if dependent.is_student:
                if age < max_age:
                    count += 1
            else:
                if age < regular_max_age:
                    count += 1
        
        return count

    @api.depends('dependent_ids', 'dependent_ids.is_dependent', 'dependent_ids.is_active')
    def _compute_dependent_count(self):
        """Calcular número de dependientes activos"""
        today = date.today()
        for employee in self:
            employee.dependent_count = employee.get_dependent_count(today)

    @api.onchange('first_name', 'second_name', 'first_last_name', 'second_last_name')
    def _onchange_name_parts(self):
        for employee in self:
            full_name = employee._compose_full_name()
            if full_name:
                employee.name = full_name

    def _compose_full_name(self, vals=None):
        self.ensure_one()
        if vals is None:
            vals = {}
        parts = [
            vals.get('first_name', self.first_name),
            vals.get('second_name', self.second_name),
            vals.get('first_last_name', self.first_last_name),
            vals.get('second_last_name', self.second_last_name),
        ]
        parts = [part for part in parts if part]
        return ' '.join(parts)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if any(key in vals for key in ('first_name', 'second_name', 'first_last_name', 'second_last_name')):
                parts = [vals.get('first_name'), vals.get('second_name'), vals.get('first_last_name'), vals.get('second_last_name')]
                parts = [part for part in parts if part]
                if parts:
                    vals['name'] = ' '.join(parts)
        return super().create(vals_list)

    def write(self, vals):
        if any(key in vals for key in ('first_name', 'second_name', 'first_last_name', 'second_last_name')):
            for employee in self:
                vals['name'] = employee._compose_full_name(vals)
        return super().write(vals)
