from odoo import models, fields, api

class TaskTemplate(models.Model):
    _name = 'project.task.template'
    _description = 'Plantilla de Tareas'

    name = fields.Char(string='Nombre de la Plantilla', required=True)
    description = fields.Text(string='Descripción')
    task_ids = fields.One2many('project.task.template.line', 'template_id', string='Tareas')
    simple_task_ids = fields.One2many('project.task.template.line', 'template_id', 
        string='Tareas Simples', domain=[('is_complex', '=', False)])
    complex_task_ids = fields.One2many('project.task.template.line', 'template_id', 
        string='Tareas Complejas', domain=[('is_complex', '=', True)])
    active = fields.Boolean(default=True)

class TaskTemplateLine(models.Model):
    _name = 'project.task.template.line'
    _description = 'Línea de Plantilla de Tarea'
    _order = 'sequence, id'

    template_id = fields.Many2one('project.task.template', string='Plantilla', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    name = fields.Char(string='Nombre de la Tarea', required=True)
    description = fields.Text(string='Descripción')
    user_ids = fields.Many2many('res.users', string='Asignar a')
    days_to_deadline = fields.Integer(string='Días hasta la fecha límite', default=0)
    is_complex = fields.Boolean(string='Es Tarea Compleja', default=False,
        help='Si está marcado, esta tarea se generará para cada categoría de producto en la orden de venta') 