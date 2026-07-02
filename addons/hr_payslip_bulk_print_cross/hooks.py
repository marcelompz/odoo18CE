# -*- coding: utf-8 -*-
"""Oculta los 2 botones redundantes del modulo l10n_py_hr_payroll_report
('Imprimir Recibo - Funcionario' y 'Imprimir Planilla IPS') modificando
DIRECTAMENTE el arch del view padre.

Se hace asi porque Odoo 18 prohibe @string y @title como selectores xpath
en herencia de vistas, y el approach con vistas hijas y xpath @name=ID
tambien fallaba. Modificar arch_db con lxml es la forma mas robusta."""
import logging

from lxml import etree

_logger = logging.getLogger(__name__)


def _hide_l10n_py_buttons(env):
    """Modifica el arch_db del view padre del l10n_py para eliminar
    los 2 botones redundantes."""
    py_module = env['ir.module.module'].search([
        ('name', '=', 'l10n_py_hr_payroll_report'),
        ('state', '=', 'installed'),
    ], limit=1)
    if not py_module:
        _logger.info('l10n_py_hr_payroll_report no instalado, skip')
        return

    parent_view = env.ref(
        'l10n_py_hr_payroll_report.view_hr_payslip_form_inherit_report_funcionario',
        raise_if_not_found=False,
    )
    if not parent_view:
        _logger.warning('Vista padre l10n_py no encontrada')
        return

    try:
        arch = parent_view.arch_db or parent_view.arch
        if not arch:
            return
        doc = etree.fromstring(arch)
        # Strings a buscar (puede que esten traducidos pero la BD guarda el original)
        targets = (
            'Imprimir Recibo - Funcionario',
            'Imprimir Planilla IPS',
        )
        removed = 0
        for btn in doc.xpath('//button'):
            s = btn.get('string') or ''
            if s in targets:
                parent = btn.getparent()
                if parent is not None:
                    parent.remove(btn)
                    removed += 1
        if removed:
            new_arch = etree.tostring(doc, encoding='unicode')
            parent_view.with_context(no_validation=True).write({
                'arch_db': new_arch,
            })
            _logger.info(
                'Eliminados %d botones del view %s (l10n_py)',
                removed, parent_view.id,
            )
        else:
            _logger.info('No se encontraron botones a ocultar (quiza ya eliminados)')
    except Exception as e:
        _logger.warning('Error ocultando botones l10n_py: %s', e)


def post_init_hook(env):
    """Hook ejecutado tras instalar/actualizar el modulo."""
    _hide_l10n_py_buttons(env)
