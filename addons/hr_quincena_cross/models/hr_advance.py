# -*- coding: utf-8 -*-
"""Extension de hr.advance con tipo "quincena" y trazabilidad de los
prestamos extraordinarios absorbidos."""
from odoo import _, fields, models


ADVANCE_TYPES = [
    ('normal', 'Anticipo normal'),
    ('quincena', 'Quincena automatica'),
]


class HrAdvance(models.Model):
    _inherit = 'hr.advance'

    advance_type = fields.Selection(
        ADVANCE_TYPES, string='Tipo de anticipo', default='normal',
        readonly=True, copy=False, tracking=True,
        help='Quincena: generado automaticamente por el wizard de quincenas. '
             'Normal: anticipo solicitado manualmente.',
    )
    quincena_date = fields.Date(
        string='Fecha de la quincena',
        readonly=True, copy=False,
    )
    quincena_loan_ids = fields.One2many(
        'hr.loan', 'quincena_advance_id',
        string='Adelantos extraordinarios incluidos',
        readonly=True,
    )
    quincena_loan_count = fields.Integer(
        string='# Adelantos incluidos',
        compute='_compute_quincena_loan_count',
    )

    # Detalle del calculo (solo informativo, para auditoria)
    quincena_dias_disponibles = fields.Integer(
        string='Dias disponibles del periodo', readonly=True, copy=False,
    )
    quincena_wage = fields.Monetary(
        string='Bruto de referencia', readonly=True, copy=False,
        currency_field='currency_id',
    )
    quincena_monto_bruto = fields.Monetary(
        string='Bruto quincena (50% prorrateado)', readonly=True, copy=False,
        currency_field='currency_id',
    )
    quincena_monto_ips = fields.Monetary(
        string='Descuento IPS quincena (4.5% prorrateado)', readonly=True, copy=False,
        currency_field='currency_id',
    )
    quincena_monto_extraordinarios = fields.Monetary(
        string='Mas: Adelantos extraordinarios', readonly=True, copy=False,
        currency_field='currency_id',
    )
    quincena_monto_cuotas_prestamo = fields.Monetary(
        string='Menos: Cuotas prestamos (50%)', readonly=True, copy=False,
        currency_field='currency_id',
    )
    quincena_monto_recupero_beneficio = fields.Monetary(
        string='Menos: Recupero beneficios/uniformes', readonly=True, copy=False,
        currency_field='currency_id',
    )

    def _compute_quincena_loan_count(self):
        for rec in self:
            rec.quincena_loan_count = len(rec.quincena_loan_ids)

    def action_view_quincena_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Adelantos incluidos en la quincena'),
            'res_model': 'hr.loan',
            'view_mode': 'list,form',
            'domain': [('quincena_advance_id', '=', self.id)],
            'context': {'create': False},
        }
