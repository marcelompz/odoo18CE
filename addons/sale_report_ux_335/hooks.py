# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Configura report.url para que wkhtmltopdf pueda cargar el HTML desde dentro del contenedor Docker."""
    env['ir.config_parameter'].sudo().set_param(
        'report.url',
        'http://127.0.0.1:8069/',
    )
