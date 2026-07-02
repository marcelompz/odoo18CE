# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cn_antiguedad_minima_prestamo_dias = fields.Integer(
        string='Antiguedad minima para Prestamo (dias)',
        default=180,
        help='Cantidad minima de dias de antiguedad que debe tener un empleado '
             'para poder solicitar un prestamo (tipo "Prestamo"). Otros tipos '
             '(Uniforme, Beneficio, Otros) no requieren antiguedad minima.',
    )
    cn_quincena_dia = fields.Integer(
        string='Dia de quincena',
        default=15,
        help='Dia del mes en que se genera la quincena (por defecto 15).',
    )
    cn_quincena_journal_id = fields.Many2one(
        'account.journal',
        string='Diario de pago de Quincenas',
        domain=[('type', 'in', ('bank', 'cash'))],
        help='Diario por defecto utilizado para pagar las quincenas generadas.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cn_antiguedad_minima_prestamo_dias = fields.Integer(
        related='company_id.cn_antiguedad_minima_prestamo_dias',
        readonly=False,
    )
    cn_quincena_dia = fields.Integer(
        related='company_id.cn_quincena_dia',
        readonly=False,
    )
    cn_quincena_journal_id = fields.Many2one(
        related='company_id.cn_quincena_journal_id',
        readonly=False,
    )
