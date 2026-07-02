# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date


class Resolucion77Config(models.Model):
    _name = 'resolucion.77.config'
    _description = 'Configuración Resolución 77 - SET'
    _rec_name = 'name'
    _check_company_auto = True

    name = fields.Char(string="Nombre de Configuración", required=True,
                      default="Configuración Resolución 77")
    
    # Configuración de fechas de cierre fiscal permitidas
    fecha_cierre_fiscal = fields.Selection([
        ('12-31', '31 de Diciembre'),
        ('04-30', '30 de Abril'),
        ('06-30', '30 de Junio')
    ], string="Fecha de Cierre Fiscal", default='12-31', required=True,
       help="Fecha de cierre del ejercicio fiscal según SET")
    
    # Porcentajes por defecto según categoría de activo
    porcentaje_edificios = fields.Float(string="% Edificios y Construcciones", default=2.5,
                                       help="Porcentaje de depreciación para edificios")
    porcentaje_maquinaria = fields.Float(string="% Maquinaria y Equipos", default=10.0,
                                        help="Porcentaje de depreciación para maquinaria")
    porcentaje_vehiculos = fields.Float(string="% Vehículos", default=20.0,
                                       help="Porcentaje de depreciación para vehículos")
    porcentaje_muebles = fields.Float(string="% Muebles y Enseres", default=10.0,
                                     help="Porcentaje de depreciación para muebles")
    porcentaje_equipos_computo = fields.Float(string="% Equipos de Cómputo", default=25.0,
                                             help="Porcentaje de depreciación para equipos de cómputo")
    porcentaje_otros = fields.Float(string="% Otros Activos", default=10.0,
                                   help="Porcentaje de depreciación para otros activos")
    
    # Configuración de valor residual
    porcentaje_residual_default = fields.Float(string="% Valor Residual por Defecto", default=10.0,
                                              help="Porcentaje por defecto para calcular valor residual")
    
    # Vida útil por defecto según categoría
    vida_util_edificios = fields.Integer(string="Vida Útil Edificios (años)", default=40,
                                        help="Vida útil por defecto para edificios")
    vida_util_maquinaria = fields.Integer(string="Vida Útil Maquinaria (años)", default=10,
                                         help="Vida útil por defecto para maquinaria")
    vida_util_vehiculos = fields.Integer(string="Vida Útil Vehículos (años)", default=5,
                                        help="Vida útil por defecto para vehículos")
    vida_util_muebles = fields.Integer(string="Vida Útil Muebles (años)", default=10,
                                      help="Vida útil por defecto para muebles")
    vida_util_equipos_computo = fields.Integer(string="Vida Útil Equipos Cómputo (años)", default=4,
                                              help="Vida útil por defecto para equipos de cómputo")
    vida_util_otros = fields.Integer(string="Vida Útil Otros (años)", default=10,
                                    help="Vida útil por defecto para otros activos")
    
    # Configuración de empresa
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        default=lambda self: self.env.company, 
        required=True,
        index=True
    )
    
    # Estado
    active = fields.Boolean(string="Activo", default=True)
    
    @api.model
    def get_default_config(self):
        """Obtiene la configuración por defecto para la compañía actual"""
        config = self.search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)
        
        if not config:
            config = self.create({
                'name': f'Configuración Resolución 77 - {self.env.company.name}',
                'company_id': self.env.company.id
            })
        
        return config
    
    def get_porcentaje_por_categoria(self, categoria):
        """Obtiene el porcentaje de depreciación según la categoría"""
        porcentajes = {
            'edificios': self.porcentaje_edificios,
            'maquinaria': self.porcentaje_maquinaria,
            'vehiculos': self.porcentaje_vehiculos,
            'muebles': self.porcentaje_muebles,
            'equipos_computo': self.porcentaje_equipos_computo,
            'otros': self.porcentaje_otros
        }
        return porcentajes.get(categoria, self.porcentaje_otros)
    
    def get_vida_util_por_categoria(self, categoria):
        """Obtiene la vida útil según la categoría"""
        vidas_utiles = {
            'edificios': self.vida_util_edificios,
            'maquinaria': self.vida_util_maquinaria,
            'vehiculos': self.vida_util_vehiculos,
            'muebles': self.vida_util_muebles,
            'equipos_computo': self.vida_util_equipos_computo,
            'otros': self.vida_util_otros
        }
        return vidas_utiles.get(categoria, self.vida_util_otros)
    
    def get_fecha_cierre_fiscal_date(self, year=None):
        """Convierte la fecha de cierre fiscal a objeto date"""
        if not year:
            year = date.today().year
            
        if self.fecha_cierre_fiscal == '12-31':
            return date(year, 12, 31)
        elif self.fecha_cierre_fiscal == '04-30':
            return date(year, 4, 30)
        elif self.fecha_cierre_fiscal == '06-30':
            return date(year, 6, 30)
        else:
            return date(year, 12, 31)  # Default


class Resolucion77CategoryTemplate(models.Model):
    _name = 'resolucion.77.category.template'
    _description = 'Plantillas de Categorías de Activos Fijos'
    _rec_name = 'name'

    name = fields.Char(string="Nombre de Categoría", required=True)
    codigo = fields.Char(string="Código", required=True)
    porcentaje_depreciacion = fields.Float(string="% Depreciación Anual", required=True)
    vida_util = fields.Integer(string="Vida Útil (años)", required=True)
    descripcion = fields.Text(string="Descripción")
    activo = fields.Boolean(string="Activo", default=True)
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                                default=lambda self: self.env.company)

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo, company_id)', 
         'El código de categoría debe ser único por compañía.')
    ] 