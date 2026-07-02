# -*- coding: utf-8 -*-
from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    cn_paga_quincena = fields.Boolean(
        string='Aplica pago de quincena',
        default=False,
        help='Si esta activo, el empleado recibe un anticipo quincenal calculado '
             'automaticamente el dia 15 (o el dia configurado en la empresa). '
             'El monto = 50% del bruto - 50% del IPS - mas anticipos extraordinarios '
             '(prestamos/uniformes) pendientes de incluir, todo prorrateado a los '
             'dias disponibles del periodo (sin descontar faltas; las faltas se '
             'descuentan unicamente en el recibo de fin de mes).',
    )
