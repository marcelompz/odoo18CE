# -*- coding: utf-8 -*-
from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # Flag existente
    appears_on_internal_payslip = fields.Boolean(
        string='Aparece en recibo INTERNO',
        default=False,
        help='Si esta marcado, esta regla aparecera en el recibo interno '
             '(Salario Bruto - IPS - Anticipos - Prestamo).',
    )

    # Flags nuevos para los recibos especificos
    appears_on_ips_receipt = fields.Boolean(
        string='Aparece en recibo IPS',
        default=False,
        help='Si esta marcado, esta regla aparecera en el recibo IPS '
             '(Salario Bruto - IPS Trabajador - Faltas - Embargo Judicial).',
    )
    appears_on_bonification_receipt = fields.Boolean(
        string='Aparece en recibo BONIFICACION',
        default=False,
        help='Si esta marcado, esta regla aparecera en el recibo de '
             'bonificaciones (BNR, BNEX, CP, HE Diurnas/Nocturnas, '
             'Feriados Diurnas/Nocturnas).',
    )
    appears_on_vacation_receipt = fields.Boolean(
        string='Aparece en recibo VACACIONES',
        default=False,
        help='Si esta marcado, esta regla aparecera en el recibo de '
             'vacaciones (CN_VACACIONES).',
    )
