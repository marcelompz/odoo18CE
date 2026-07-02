# -*- coding: utf-8 -*-
"""Migration 18.0.1.0.18 - auto-instala python-docx."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    try:
        from odoo.addons.hr_job_description_cross.hooks import _ensure_python_docx
        _ensure_python_docx()
    except Exception as e:
        _logger.warning(
            'No se pudo auto-instalar python-docx en migracion: %s', e
        )
