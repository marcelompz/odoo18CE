# -*- coding: utf-8 -*-
"""Migration 18.0.1.0.17 - asigna manual_code a puestos preexistentes."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Asegurar que la secuencia existe (cargada por data/ir_sequence_data.xml)
    seq = env['ir.sequence'].search([('code', '=', 'hr.job.manual.code')], limit=1)
    if not seq:
        _logger.warning(
            'Secuencia hr.job.manual.code no encontrada; creando fallback.'
        )
        seq = env['ir.sequence'].create({
            'name': 'Codigo de Manual de Funciones',
            'code': 'hr.job.manual.code',
            'prefix': 'MF/%(year)s/',
            'padding': 5,
            'number_next': 1,
            'number_increment': 1,
        })

    # Asignar codigo a puestos sin manual_code
    jobs = env['hr.job'].search([('manual_code', '=', False)])
    _logger.info('Asignando manual_code a %s puestos preexistentes.', len(jobs))
    for job in jobs:
        try:
            job.manual_code = env['ir.sequence'].next_by_code(
                'hr.job.manual.code'
            ) or '/'
        except Exception as e:
            _logger.warning(
                'No se pudo asignar manual_code al puesto %s: %s', job.name, e
            )
