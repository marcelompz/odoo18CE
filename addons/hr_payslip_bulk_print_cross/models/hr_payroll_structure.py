# -*- coding: utf-8 -*-
"""Action en hr.payroll.structure para aplicar automaticamente los flags
de recibos (IPS / Interno / Bonificacion / Vacaciones) sobre las reglas
salariales segun el diseno predefinido de Crossnexion."""
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


# Mapeo: por cada flag, lista de codigos de regla que deben tenerlo en True.
# Una misma regla puede aparecer en mas de un flag (ej. CN_SALARIO_BRUTO esta
# tanto en IPS como en INTERNO).
RECEIPT_FLAGS_MAPPING = {
    'appears_on_ips_receipt': [
        'CN_SALARIO_BRUTO',
        'CN_IPS_TRAB',
        'CN_FALTAS',
        'PY_DESC_NO_REM',
        'CN_EMBARGO',
    ],
    'appears_on_internal_payslip': [
        'CN_SALARIO_BRUTO',
        'CN_IPS_TRAB',
        'CN_ANTICIPO',
        'CN_ANTICIPO_EXTRA',
        'CN_PRESTAMO',
    ],
    'appears_on_bonification_receipt': [
        'BNR', 'BNEX', 'CP', 'BNFM',
        'CN_HE_DIA', 'CN_HE_NOCHE',
        'CN_FERIADO_DIA', 'CN_FERIADO_NOCHE',
        'PY_FERIADO_DIA', 'PY_FERIADO_NOCHE',
    ],
    'appears_on_vacation_receipt': [
        'CN_VACACIONES',
    ],
}

ALL_FLAGS = list(RECEIPT_FLAGS_MAPPING.keys())


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def action_apply_receipt_flags(self):
        """Aplica el mapeo predefinido de flags de recibos a las reglas
        salariales: resetea los 4 flags en TODAS las reglas y luego marca
        en True los codigos correspondientes segun RECEIPT_FLAGS_MAPPING.
        La accion es global (afecta a todas las reglas de todas las
        estructuras), por eso solo necesita una estructura seleccionada
        para disparar el proceso."""
        Rule = self.env['hr.salary.rule'].with_context(active_test=False)
        # 1) Reset
        all_rules = Rule.search([])
        all_rules.write({flag: False for flag in ALL_FLAGS})
        _logger.info(
            'action_apply_receipt_flags: reset flags en %s reglas',
            len(all_rules),
        )
        # 2) Re-aplicar segun mapeo
        applied_summary = {}
        for flag, codes in RECEIPT_FLAGS_MAPPING.items():
            rules = Rule.search([('code', 'in', codes)])
            if rules:
                rules.write({flag: True})
            applied_summary[flag] = len(rules)
            _logger.info(
                'action_apply_receipt_flags: %s = True en %s reglas (codes=%s)',
                flag, len(rules), codes,
            )
        # 3) Mensaje al usuario
        msg_lines = ['Flags de recibos aplicados:']
        for flag, count in applied_summary.items():
            short_name = flag.replace('appears_on_', '').replace('_', ' ').upper()
            msg_lines.append('- %s: %s reglas marcadas' % (short_name, count))
        msg = '\n'.join(msg_lines)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Flags de recibos PY'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            },
        }

    def action_set_default_report_to_ips(self):
        """Asigna 'Recibo IPS (2 copias)' como reporte por defecto de las
        estructuras seleccionadas. Esto cambia el PDF preview que se
        muestra en el panel lateral del recibo de nomina, asi se ve la
        version compacta con cabecera MTESS en lugar del recibo estandar
        de Odoo."""
        if 'report_id' not in self._fields:
            from odoo.exceptions import UserError
            raise UserError(_(
                'El campo report_id no existe en hr.payroll.structure '
                '(posiblemente no esta instalado hr_payroll_account u otra '
                'dependencia que lo agrega).'
            ))
        ips_report = self.env.ref(
            'hr_payslip_bulk_print_cross.action_report_recibo_ips_a5',
            raise_if_not_found=False,
        )
        if not ips_report:
            from odoo.exceptions import UserError
            raise UserError(_('No se encontro la accion de reporte Recibo IPS.'))
        updated = 0
        for struct in self:
            if struct.report_id != ips_report:
                struct.report_id = ips_report.id
                updated += 1
        msg = (
            'Recibo IPS asignado como reporte por defecto en %s estructura(s). '
            'El panel lateral del recibo ahora mostrara el PDF compacto '
            'con cabecera MTESS.'
        ) % updated
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reporte por defecto'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }
