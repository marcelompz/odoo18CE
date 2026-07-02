# -*- coding: utf-8 -*-
"""v18.0.1.0.5: marcar puestos existentes como 'approved' por defecto."""
import logging
from odoo import api, SUPERUSER_ID, fields
from odoo.addons.hr_job_description_cross.hooks import post_init_hook

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    jobs = env['hr.job'].search([('manual_state', 'in', (False, ''))])
    if jobs:
        _logger.info('Marcando %s puestos preexistentes como approved', len(jobs))
        jobs.write({
            'manual_state': 'approved',
            'manual_create_date': fields.Datetime.now(),
        })
    try:
        post_init_hook(env)
    except Exception as e:
        _logger.warning('Hook portal fallo: %s', e)
