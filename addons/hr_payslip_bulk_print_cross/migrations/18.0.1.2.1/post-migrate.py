# -*- coding: utf-8 -*-
"""Elimina registros del reporte MTESS Planilla viejo, reemplazado por
los 4 recibos compactos (IPS, Interno, Bonificacion, Vacaciones)
en la version 18.0.1.2.0."""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    _logger.info('Eliminando reporte MTESS Planilla viejo (reemplazado por '
                 'los 4 recibos compactos)')
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Eliminar la accion de reporte vieja
    try:
        old_report = env['ir.actions.report'].search([
            ('report_name', '=',
             'hr_payslip_bulk_print_cross.report_payslip_mtess_planilla'),
        ])
        if old_report:
            _logger.info('Eliminando ir.actions.report viejo: %s ids',
                         len(old_report))
            old_report.unlink()
    except Exception as e:
        _logger.warning('No se pudo eliminar ir.actions.report viejo: %s', e)

    # 2) Eliminar el QWeb template viejo
    try:
        old_views = env['ir.ui.view'].search([
            '|',
            ('key', '=',
             'hr_payslip_bulk_print_cross.report_payslip_mtess_planilla'),
            ('name', '=',
             'hr_payslip_bulk_print_cross.report_payslip_mtess_planilla'),
        ])
        if old_views:
            _logger.info('Eliminando ir.ui.view viejo: %s ids', len(old_views))
            old_views.unlink()
    except Exception as e:
        _logger.warning('No se pudo eliminar ir.ui.view viejo: %s', e)

    # 3) Eliminar el paperformat viejo si nadie lo usa
    try:
        old_paperformat = env['report.paperformat'].search([
            ('name', '=', 'MTESS Recibo - Margenes Minimos'),
        ])
        if old_paperformat:
            # Verificar que ningun ir.actions.report lo este usando
            in_use = env['ir.actions.report'].search([
                ('paperformat_id', 'in', old_paperformat.ids),
            ], limit=1)
            if not in_use:
                _logger.info('Eliminando paperformat viejo: %s ids',
                             len(old_paperformat))
                old_paperformat.unlink()
    except Exception as e:
        _logger.warning('No se pudo eliminar paperformat viejo: %s', e)

    # 4) Limpiar referencias huerfanas en ir.model.data
    try:
        old_imd = env['ir.model.data'].search([
            ('module', '=', 'hr_payslip_bulk_print_cross'),
            ('name', 'in', [
                'action_report_payslip_mtess_planilla',
                'paperformat_payslip_mtess',
                'report_payslip_mtess_planilla',
            ]),
        ])
        if old_imd:
            _logger.info('Eliminando ir.model.data huerfanos: %s ids',
                         len(old_imd))
            old_imd.unlink()
    except Exception as e:
        _logger.warning('No se pudo limpiar ir.model.data: %s', e)

    _logger.info('Limpieza completada')
