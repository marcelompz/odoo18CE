# -*- coding: utf-8 -*-
"""Migracion 18.0.1.2.11:
* Re-crea/actualiza la vista que oculta los 2 botones del modulo
  l10n_py_hr_payroll_report ('Imprimir Recibo - Funcionario' y
  'Imprimir Planilla IPS')."""
from odoo import api, SUPERUSER_ID

from odoo.addons.hr_payslip_bulk_print_cross.hooks import _hide_l10n_py_buttons


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _hide_l10n_py_buttons(env)
