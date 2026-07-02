# -*- coding: utf-8 -*-
"""Hooks de instalacion/actualizacion del modulo Manual de Funciones."""
import logging
import subprocess
import sys

_logger = logging.getLogger(__name__)


def _ensure_python_docx():
    """Intenta importar python-docx; si falla, lo instala via pip."""
    try:
        import docx  # noqa: F401
        _logger.info('python-docx ya esta instalado.')
        return True
    except ImportError:
        _logger.info('python-docx no esta instalado. Intentando instalar...')
        # Estrategia 1: pip install --break-system-packages (Ubuntu 23+/Debian 12+)
        for cmd in (
            [sys.executable, '-m', 'pip', 'install', 'python-docx',
             '--break-system-packages', '--quiet'],
            [sys.executable, '-m', 'pip', 'install', 'python-docx', '--quiet'],
            ['pip3', 'install', 'python-docx',
             '--break-system-packages', '--quiet'],
            ['pip', 'install', 'python-docx',
             '--break-system-packages', '--quiet'],
        ):
            try:
                _logger.info('Ejecutando: %s', ' '.join(cmd))
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    _logger.info('python-docx instalado correctamente.')
                    # Verificar el import
                    try:
                        import importlib
                        if 'docx' in sys.modules:
                            importlib.reload(sys.modules['docx'])
                        import docx  # noqa: F401
                        return True
                    except ImportError:
                        _logger.warning(
                            'Instalacion completada pero el modulo docx '
                            'no es importable en este proceso. Sera '
                            'visible despues de reiniciar Odoo.'
                        )
                        return True
                else:
                    _logger.warning(
                        'Comando fallo (rc=%s): %s', result.returncode,
                        result.stderr.strip()[:300]
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError,
                    OSError) as e:
                _logger.warning('No se pudo ejecutar %s: %s', cmd[0], e)
                continue
        _logger.error(
            'No se pudo instalar python-docx automaticamente. '
            'Ejecute manualmente dentro del contenedor: '
            'pip install python-docx --break-system-packages'
        )
        return False


def _portal_tile(env):
    """Si hr_portal_cross esta instalado, agrega un tile 'Puestos por
    Departamento' al portal Talento Humano."""
    portal_module = env['ir.module.module'].search([
        ('name', '=', 'hr_portal_cross'),
        ('state', '=', 'installed'),
    ], limit=1)
    if not portal_module:
        _logger.info('hr_portal_cross no instalado, skip tile')
        return

    Tile = env.get('talent.portal.tile')
    if not Tile:
        return

    category = env.ref('hr_portal_cross.cat_employees',
                       raise_if_not_found=False)
    action = env.ref(
        'hr_job_description_cross.action_hr_job_by_department',
        raise_if_not_found=False,
    )
    if not action:
        return

    existing = Tile.search([
        ('name', '=', 'Puestos por Departamento'),
    ], limit=1)
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
        _logger.info('Tile "Puestos por Departamento" actualizado')
    else:
        vals['name'] = 'Puestos por Departamento'
        Tile.create(vals)
        _logger.info('Tile "Puestos por Departamento" creado')


def post_init_hook(env):
    _ensure_python_docx()
    _portal_tile(env)


def post_load():
    """Se ejecuta al cargar el modulo (incluso sin actualizar). Asegura
    que python-docx este presente para que el boton 'Exportar a Word'
    funcione siempre."""
    try:
        _ensure_python_docx()
    except Exception as e:
        _logger.warning('post_load fallo silenciosamente: %s', e)
