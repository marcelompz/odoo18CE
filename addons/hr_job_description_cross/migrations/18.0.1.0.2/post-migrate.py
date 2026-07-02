# -*- coding: utf-8 -*-
"""Migracion 18.0.1.0.2: si la v1.0.1 habia creado manual_skill_ids,
ya no se usa. El campo desaparece y los valores quedan en BD pero el
modelo no los referencia. La columna fkey se elimina automaticamente
al perder la declaracion."""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Si hr_portal_cross esta instalado, asegurar el tile (idempotente)
    portal_module = env['ir.module.module'].search([
        ('name', '=', 'hr_portal_cross'),
        ('state', '=', 'installed'),
    ], limit=1)
    if not portal_module:
        return

    Tile = env.get('talent.portal.tile')
    if not Tile:
        return

    category = env.ref('hr_portal_cross.cat_employees', raise_if_not_found=False)
    action = env.ref(
        'hr_job_description_cross.action_hr_job_by_department',
        raise_if_not_found=False,
    )
    if not action:
        return

    existing = Tile.search([('name', '=', 'Puestos por Departamento')], limit=1)
    vals = {
        'description': 'Estructura de puestos por departamento',
        'icon_class': 'fa-sitemap',
        'action_xml_id': 'hr_job_description_cross.action_hr_job_by_department',
        'category_id': category.id if category else False,
        'color': '7',
        'sequence': 35,
    }
    if existing:
        existing.write(vals)
    else:
        vals['name'] = 'Puestos por Departamento'
        Tile.create(vals)
    _logger.info('Tile Puestos por Departamento configurado')
