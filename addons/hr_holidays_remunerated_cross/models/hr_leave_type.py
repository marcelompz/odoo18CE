# -*- coding: utf-8 -*-
from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_remunerated_default = fields.Boolean(
        string='Es remunerado por defecto',
        default=True,
        help='Valor por defecto que se aplicara al campo "Es remunerado" '
             'cuando se cree una solicitud de este tipo. El gerente puede '
             'cambiarlo al aprobar.',
    )
