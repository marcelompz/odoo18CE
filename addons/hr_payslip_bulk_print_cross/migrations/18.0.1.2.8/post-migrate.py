# -*- coding: utf-8 -*-
"""Migracion 18.0.1.2.8:
* Copia el valor de hr.salary.rule.appears_on_payslip a appears_on_ips_receipt
  para todas las reglas existentes que tengan appears_on_payslip=True y NO
  tengan appears_on_ips_receipt todavia (idempotente).
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    rules = env['hr.salary.rule'].with_context(active_test=False).search([
        ('appears_on_payslip', '=', True),
        ('appears_on_ips_receipt', '=', False),
    ])
    if rules:
        _logger.info('Copiando appears_on_payslip -> appears_on_ips_receipt en %s reglas',
                     len(rules))
        rules.write({'appears_on_ips_receipt': True})
    else:
        _logger.info('No hay reglas con appears_on_payslip=True para migrar')
