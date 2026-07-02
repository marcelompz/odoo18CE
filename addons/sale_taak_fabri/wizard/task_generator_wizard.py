from odoo import models, fields, api
from datetime import datetime, timedelta

class TaskGeneratorSimpleTask(models.TransientModel):
    _name = 'sale.task.generator.simple.task'
    _description = 'Tarea Simple'

    wizard_id = fields.Many2one('sale.task.generator.wizard', string='Wizard')
    name = fields.Char(string='Nombre de la Tarea', required=True)
    user_ids = fields.Many2many('res.users', string='Asignar a')
    date_deadline = fields.Date(string='Fecha Límite')

class TaskGeneratorComplexTask(models.TransientModel):
    _name = 'sale.task.generator.complex.task'
    _description = 'Tarea Compleja'

    wizard_id = fields.Many2one('sale.task.generator.wizard', string='Wizard')
    name = fields.Char(string='Nombre de la Tarea', required=True)
    user_ids = fields.Many2many('res.users', string='Asignar a')
    date_deadline = fields.Date(string='Fecha Límite')

class TaskGeneratorWizard(models.TransientModel):
    _name = 'sale.task.generator.wizard'
    _description = 'Generador de Tareas desde Orden de Venta'

    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True)
    project_id = fields.Many2one('project.project', string='Proyecto', required=True)
    template_id = fields.Many2one('project.task.template', string='Plantilla de Tareas')
    simple_task_ids = fields.One2many('sale.task.generator.simple.task', 'wizard_id', string='Tareas Simples')
    complex_task_ids = fields.One2many('sale.task.generator.complex.task', 'wizard_id', string='Tareas Complejas')
    validity_date = fields.Date(related='sale_order_id.validity_date', string='Fecha de Vencimiento', readonly=True)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            # Limpiar tareas existentes
            self.simple_task_ids = [(5, 0, 0)]
            self.complex_task_ids = [(5, 0, 0)]
            
            # Crear nuevas tareas desde la plantilla
            today = fields.Date.today()
            validity_date = self.sale_order_id.validity_date or (today + timedelta(days=30))
            
            for task in self.template_id.task_ids:
                if task.is_complex:
                    self.complex_task_ids = [(0, 0, {
                        'name': task.name,
                        'user_ids': [(6, 0, task.user_ids.ids)],
                        'date_deadline': validity_date,
                    })]
                else:
                    self.simple_task_ids = [(0, 0, {
                        'name': task.name,
                        'user_ids': [(6, 0, task.user_ids.ids)],
                        'date_deadline': validity_date,
                    })]

    def action_generate_tasks(self):
        self.ensure_one()
        SaleOrder = self.env['sale.order']
        ProjectTask = self.env['project.task']

        # Obtener fechas
        today = fields.Date.today()
        validity_date = self.sale_order_id.validity_date or (today + timedelta(days=30))
        
        # Obtener categorías únicas de productos
        categories = self.sale_order_id.order_line.mapped('product_id.categ_id')
        
        # Calcular total de subtareas
        total_subtasks = len(self.simple_task_ids) + (len(self.complex_task_ids) * len(categories))
        
        # Calcular días entre cada subtarea
        days_between = (validity_date - today).days / (total_subtasks + 1) if total_subtasks > 0 else 0

        # Crear tarea principal
        main_task = ProjectTask.create({
            'name': f"{self.sale_order_id.name} {self.sale_order_id.partner_id.name}",
            'project_id': self.project_id.id,
            'sale_order_id': self.sale_order_id.id,
            'date_deadline': validity_date,
        })

        # Contador para distribuir las fechas
        subtask_counter = 0

        # Crear tareas simples
        for simple_task in self.simple_task_ids:
            subtask_counter += 1
            subtask_deadline = today + timedelta(days=int(days_between * subtask_counter))
            ProjectTask.create({
                'name': f"{self.sale_order_id.name} {simple_task.name}",
                'project_id': self.project_id.id,
                'parent_id': main_task.id,
                'sale_order_id': self.sale_order_id.id,
                'user_ids': [(6, 0, simple_task.user_ids.ids)],
                'date_deadline': simple_task.date_deadline or subtask_deadline,
            })

        # Crear tareas complejas
        for complex_task in self.complex_task_ids:
            for category in categories:
                subtask_counter += 1
                subtask_deadline = today + timedelta(days=int(days_between * subtask_counter))
                ProjectTask.create({
                    'name': f"{self.sale_order_id.name} {complex_task.name} {category.name}",
                    'project_id': self.project_id.id,
                    'parent_id': main_task.id,
                    'sale_order_id': self.sale_order_id.id,
                    'product_category_id': category.id,
                    'user_ids': [(6, 0, complex_task.user_ids.ids)],
                    'date_deadline': complex_task.date_deadline or subtask_deadline,
                })

        return {'type': 'ir.actions.act_window_close'} 