# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_open_bulk_print_wizard(self):
        """Abre el asistente de impresion masiva con todos los recibos
        contenidos en el/los lote(s) seleccionado(s)."""
        if not self:
            raise UserError(_('Debe seleccionar al menos un lote de nomina.'))
        slips = self.mapped('slip_ids')
        if not slips:
            raise UserError(_('El/los lote(s) seleccionado(s) no contienen recibos.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imprimir Recibos en Masa'),
            'res_model': 'hr.payslip.bulk.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'hr.payslip.run',
                'active_ids': self.ids,
                'default_payslip_ids': [(6, 0, slips.ids)],
            },
        }

    def action_open_batch_review_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Revisar Lote de Nómina'),
            'res_model': 'hr.payslip.batch.review.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
                'default_company_id': self.company_id.id,
            },
        }

    def action_print_planilla_ips(self):
        """Imprime la Planilla IPS oficial (formato MTESS) para todos los
        recibos del lote seleccionado. Usa el reporte
        'l10n_py_hr_payroll_report.action_report_payslip_ips' que ya existe
        en el modulo de localizacion PY."""
        if not self:
            raise UserError(_('Debe seleccionar al menos un lote de nomina.'))
        slips = self.mapped('slip_ids')
        if not slips:
            raise UserError(_('El/los lote(s) seleccionado(s) no contienen recibos.'))
        report = self.env.ref(
            'l10n_py_hr_payroll_report.action_report_payslip_ips',
            raise_if_not_found=False,
        )
        if not report:
            raise UserError(_(
                'No se encontro el reporte Planilla IPS. Verifique que el '
                'modulo l10n_py_hr_payroll_report este instalado.'
            ))
        return report.report_action(slips)
