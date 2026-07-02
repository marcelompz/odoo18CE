# -*- coding: utf-8 -*-
"""Migration 18.0.1.6.2 - actualiza tile_holidays para apuntar al nuevo
modelo talent.holiday y agrega los tiles tile_recruitment y tile_job_manual
si faltan."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    Tile = env['talent.portal.tile']

    # 1. Actualizar tile_holidays para apuntar al nuevo action
    tile_h = env.ref('hr_portal_cross.tile_holidays', raise_if_not_found=False)
    if tile_h:
        tile_h.write({
            'name': 'Dias Festivos',
            'description': 'Feriados con imagenes y avisos',
            'icon_class': 'fa-flag',
            'action_xml_id': 'hr_portal_cross.action_talent_holiday',
        })
        _logger.info('tile_holidays actualizado al nuevo action.')

    # Buscar tambien por nombre por si el XMLID no existe
    others = Tile.search([
        ('name', '=', 'Dias Festivos'),
        ('action_xml_id', '=', 'hr_holidays.open_view_global_leave'),
    ])
    if others:
        others.write({
            'action_xml_id': 'hr_portal_cross.action_talent_holiday',
            'description': 'Feriados con imagenes y avisos',
        })
        _logger.info('Actualizados %s tiles con accion vieja.', len(others))

    # 2. Asegurar que existan tile_recruitment y tile_job_manual
    cat_employees = env.ref('hr_portal_cross.cat_employees',
                            raise_if_not_found=False)

    tile_rec = env.ref('hr_portal_cross.tile_recruitment',
                       raise_if_not_found=False)
    if not tile_rec:
        # Crear con XMLID
        vals_rec = {
            'name': 'Reclutamiento',
            'description': 'Procesos de reclutamiento y seleccion',
            'icon_class': 'fa-user-plus',
            'color': '5',
            'sequence': 13,
            'category_id': cat_employees.id if cat_employees else False,
            'action_xml_id': 'hr_recruitment.action_hr_job',
        }
        rec = Tile.create(vals_rec)
        env['ir.model.data'].create({
            'name': 'tile_recruitment',
            'module': 'hr_portal_cross',
            'model': 'talent.portal.tile',
            'res_id': rec.id,
            'noupdate': True,
        })
        _logger.info('tile_recruitment creado.')

    tile_jm = env.ref('hr_portal_cross.tile_job_manual',
                      raise_if_not_found=False)
    if not tile_jm:
        vals_jm = {
            'name': 'Manual de Funciones',
            'description': 'Descripcion de funciones por puesto',
            'icon_class': 'fa-book',
            'color': '9',
            'sequence': 14,
            'category_id': cat_employees.id if cat_employees else False,
            'action_xml_id': 'hr_job_description_cross.action_hr_job_by_department',
        }
        jm = Tile.create(vals_jm)
        env['ir.model.data'].create({
            'name': 'tile_job_manual',
            'module': 'hr_portal_cross',
            'model': 'talent.portal.tile',
            'res_id': jm.id,
            'noupdate': True,
        })
        _logger.info('tile_job_manual creado.')
