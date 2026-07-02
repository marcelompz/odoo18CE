# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import logging

_logger = logging.getLogger(__name__)

class HrPayrollReportWizard(models.TransientModel):
    _name = 'hr.payroll.report.wizard'
    _description = 'Generador de Reportes Legales de Nómina (MTESS/DNIT)'

    report_type = fields.Selection([
        ('mtess_monthly', 'MTESS - Planilla Laboral Mensual'),
        ('mtess_employees', 'MTESS - Libro Registro de Empleados y Obreros'),
        ('mtess_vacations', 'MTESS - Libro Registro de Vacaciones'),
        ('dnit_salary', 'DNIT - Listado Nómina Salarial'),
        ('payroll_summary', 'Planilla de Salarios (Resumen por Conceptos)'),
    ], string='Tipo de Reporte', required=True, default='mtess_monthly')

    date_from = fields.Date(string='Fecha Inicio', required=False, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='Fecha Fin', required=False, default=lambda self: fields.Date.context_today(self))
    
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lote de Nómina')

    def action_generate_xlsx(self):
        self.ensure_one()
        if self.report_type == 'payroll_summary' and not self.payslip_run_id:
            raise UserError("Seleccione un lote de nómina para generar la planilla de salarios.")
        if self.report_type == 'mtess_monthly':
            if not self.payslip_run_id and (not self.date_from or not self.date_to):
                raise UserError("Indique un lote de nómina o un rango de fechas para este reporte.")
        elif self.report_type != 'payroll_summary' and (not self.date_from or not self.date_to):
            raise UserError("Debe indicar el rango de fechas para este reporte.")
        # Aquí se llamará a la lógica de generación específica para cada reporte
        # Por ahora solo retornamos una acción vacía o un mensaje
        if self.report_type == 'mtess_monthly':
            return self._generate_mtess_monthly_report()
        elif self.report_type == 'mtess_employees':
            return self._generate_mtess_employees_report()
        elif self.report_type == 'mtess_vacations':
            return self._generate_mtess_vacations_report()
        elif self.report_type == 'dnit_salary':
            return self._generate_dnit_salary_report()
        elif self.report_type == 'payroll_summary':
            return self._generate_payroll_summary_report()
        
        return {'type': 'ir.actions.act_window_close'}

    def _generate_payroll_summary_report(self):
        # Este método está implementado en hr_payroll_report_xlsx.py vía _inherit
        raise UserError(_("La generación de la Planilla de Salarios requiere que el módulo hr_payroll_report_xlsx esté correctamente cargado."))





    def _generate_mtess_vacations_report(self):
        # Este método está implementado en hr_payroll_report_xlsx.py vía _inherit
        # Si se llama desde aquí, el módulo xlsx debería estar cargado
        # Si no está disponible, lanzar error
        raise UserError(_("La generación del Libro de Vacaciones MTESS requiere que el módulo hr_payroll_report_xlsx esté correctamente cargado."))

    def _generate_dnit_salary_report(self):
        # Este método está implementado en hr_payroll_report_xlsx.py vía _inherit
        # Si se llama desde aquí, el módulo xlsx debería estar cargado
        # Si no está disponible, lanzar error
        raise UserError(_("La generación del Listado Nómina Salarial DNIT requiere que el módulo hr_payroll_report_xlsx esté correctamente cargado."))
