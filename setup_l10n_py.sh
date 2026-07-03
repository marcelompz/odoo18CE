#!/bin/bash
# Setup script para módulos l10n_py en el servidor
set -e

L10N_PY_DIR="/srv/odoo-modules/l10n_py"
GITHUB_SSH="git@github.com:marcelompz/odoo-l10n-py.git"

echo "=== Setup de módulos l10n_py ==="

if [ -d "$L10N_PY_DIR/.git" ]; then
    echo "Repositorio ya existe, actualizando..."
    cd "$L10N_PY_DIR"
    git pull origin main
else
    echo "Clonando repositorio con SSH..."
    mkdir -p /srv/odoo-modules
    git clone "$GITHUB_SSH" "$L10N_PY_DIR"
fi

echo "✓ Módulos listos en $L10N_PY_DIR"

# Instalar dependencia Python en el HOST
echo ""
echo "=== Instalando dependencia tu-ruc-python-client ==="
pip3 install --break-system-packages tu-ruc-python-client 2>&1 | tail -3
echo "✓ tu-ruc-python-client instalado"

ls -la "$L10N_PY_DIR"
