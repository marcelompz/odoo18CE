from odoo import api, models

class ReportPayslipFuncionario(models.AbstractModel):
    _name = 'report.l10n_py_hr_payroll_report.report_payslip_funcionario'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'data': data,
        }

