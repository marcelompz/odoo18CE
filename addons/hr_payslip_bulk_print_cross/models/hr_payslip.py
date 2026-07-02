# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # ================================================================
    # Computeds para ocultar botones cuando no aplica el recibo
    # ================================================================
    has_bonification = fields.Boolean(
        string='Tiene bonificaciones',
        compute='_compute_recibo_flags',
        help='True si alguna linea con appears_on_bonification_receipt '
             'tiene total != 0.',
    )
    has_vacation = fields.Boolean(
        string='Tiene vacaciones',
        compute='_compute_recibo_flags',
        help='True si alguna linea con appears_on_vacation_receipt '
             'tiene total != 0.',
    )

    @api.depends('line_ids', 'line_ids.total')
    def _compute_recibo_flags(self):
        for slip in self:
            bonif_lines = slip.line_ids.filtered(
                lambda l: l.salary_rule_id.appears_on_bonification_receipt
                and l.total
            )
            vac_lines = slip.line_ids.filtered(
                lambda l: l.salary_rule_id.appears_on_vacation_receipt
                and l.total
            )
            slip.has_bonification = bool(bonif_lines)
            slip.has_vacation = bool(vac_lines)

    # ================================================================
    # Acciones de impresion individual
    # ================================================================
    def action_print_recibo_ips(self):
        self.ensure_one()
        return self.env.ref(
            'hr_payslip_bulk_print_cross.action_report_recibo_ips_a5'
        ).report_action(self)

    def action_print_recibo_interno(self):
        self.ensure_one()
        return self.env.ref(
            'hr_payslip_bulk_print_cross.action_report_recibo_interno_a5'
        ).report_action(self)

    def action_print_recibo_bonificacion(self):
        self.ensure_one()
        if not self.has_bonification:
            raise UserError(_(
                'Este recibo no tiene bonificaciones (BNR / BNEX / CP / '
                'HE / Feriados) con valor distinto de cero.'
            ))
        return self.env.ref(
            'hr_payslip_bulk_print_cross.action_report_recibo_bonificacion'
        ).report_action(self)

    def action_print_recibo_vacaciones(self):
        self.ensure_one()
        if not self.has_vacation:
            raise UserError(_(
                'Este recibo no tiene vacaciones calculadas '
                '(CN_VACACIONES) con valor distinto de cero.'
            ))
        return self.env.ref(
            'hr_payslip_bulk_print_cross.action_report_recibo_vacaciones_a5'
        ).report_action(self)

    # ================================================================
    # Wizard masivo (existente)
    # ================================================================

    def action_print_planilla_ips_individual(self):
        """Imprime la Planilla IPS oficial (formato MTESS) para este recibo
        individual. Usa el reporte de l10n_py_hr_payroll_report."""
        self.ensure_one()
        report = self.env.ref(
            'l10n_py_hr_payroll_report.action_report_payslip_ips',
            raise_if_not_found=False,
        )
        if not report:
            raise UserError(_(
                'No se encontro el reporte Planilla IPS. Verifique que el '
                'modulo l10n_py_hr_payroll_report este instalado.'
            ))
        return report.report_action(self)

    def action_open_bulk_print_wizard(self):
        """Abre el asistente de impresion masiva con los recibos
        seleccionados."""
        if not self:
            raise UserError(_('Debe seleccionar al menos un recibo de nomina.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imprimir Recibos en Masa'),
            'res_model': 'hr.payslip.bulk.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'hr.payslip',
                'active_ids': self.ids,
                'default_payslip_ids': [(6, 0, self.ids)],
            },
        }
