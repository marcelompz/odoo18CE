# -*- coding: utf-8 -*-
"""Migration 18.0.1.0.19 - backfill creador y proxima revision."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Bypass cualquier write-lock por manual aprobado
    env = env(context=dict(env.context, skip_manual_lock=True))

    admin = env.ref('base.user_admin', raise_if_not_found=False) or env.user
    jobs = env['hr.job'].search([('manual_creator_id', '=', False)])
    _logger.info('Backfill manual_creator_id en %s puestos.', len(jobs))
    for job in jobs:
        try:
            uid = job.create_uid.id if job.create_uid else admin.id
            job.manual_creator_id = uid
        except Exception as e:
            _logger.warning('No se pudo asignar creador a %s: %s', job.name, e)

    all_jobs = env['hr.job'].search([('manual_create_date', '!=', False)])
    all_jobs._compute_manual_next_revision()
    _logger.info('Recomputado proxima revision en %s puestos.', len(all_jobs))
