# -*- coding: utf-8 -*-
"""Migracion 18.0.1.0.4: re-ejecuta el hook para asegurar tile portal."""
from odoo import api, SUPERUSER_ID
from odoo.addons.hr_job_description_cross.hooks import post_init_hook


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    post_init_hook(env)
