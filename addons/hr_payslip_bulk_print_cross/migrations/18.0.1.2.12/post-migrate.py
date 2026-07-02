# -*- coding: utf-8 -*-
"""Migracion 18.0.1.2.12: re-ejecuta la ocultacion de botones del l10n_py
por approach lxml (modificacion directa del arch del view padre)."""
from odoo import api, SUPERUSER_ID

from odoo.addons.hr_payslip_bulk_print_cross.hooks import _hide_l10n_py_buttons


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _hide_l10n_py_buttons(env)
