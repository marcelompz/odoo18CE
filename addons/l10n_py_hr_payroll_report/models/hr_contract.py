# -*- coding: utf-8 -*-
from odoo import fields, models, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    contract_template_id = fields.Many2one(
        'hr.contract.template',
        string='Plantilla de Contrato',
        help='Selecciona la plantilla de contrato a usar para generar el documento'
    )
    contract_html_content = fields.Html(
        string='Contenido del Contrato',
        help='Contenido HTML editable del contrato. Se carga automáticamente desde la plantilla seleccionada.'
    )

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        """Cargar el contenido HTML de la plantilla cuando se selecciona y reemplazar variables"""
        if self.contract_template_id and self.contract_template_id.description:
            # Obtener el HTML de la plantilla
            html_content = self.contract_template_id.description
            
            # Reemplazar las variables con los datos del contrato actual
            # Usamos el método del reporte para hacer el reemplazo
            try:
                report_model = self.env['report.l10n_py_hr_payroll_report.report_contract_py']
                if hasattr(report_model, '_replace_contract_variables'):
                    html_content = report_model._replace_contract_variables(
                        html_content, 
                        self, 
                        self.contract_template_id
                    )
            except Exception:
                # Si hay algún error al reemplazar variables, usar el contenido sin reemplazar
                # Esto puede pasar si el contrato aún no tiene todos los datos necesarios
                pass
            
            self.contract_html_content = html_content

