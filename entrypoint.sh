#!/bin/bash
set -e

# ============================================
# Entrypoint optimizado para Odoo 18 en Docker
# ============================================

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# ============================================
# Validación de variables de entorno
# ============================================

log_info "Iniciando entrypoint optimizado para Odoo"

# Verificar variables críticas de PostgreSQL
if [ -z "$PGHOST" ]; then
    log_warn "PGHOST no definido, usando valor por defecto: db_odoo"
    export PGHOST="db_odoo"
fi

if [ -z "$PGDATABASE" ]; then
    log_warn "PGDATABASE no definido, usando valor por defecto: odoo_production"
    export PGDATABASE="odoo_production"
fi

if [ -z "$PGPASSWORD" ]; then
    log_error "PGPASSWORD no definida. La conexión a la base de datos puede fallar."
fi

if [ -z "$PGDATABASE" ]; then
    log_warn "PGDATABASE no definido, usando valor por defecto: odoo_prod_9090"
    export PGDATABASE="odoo_prod_9090"
fi

# ============================================
# Esperar a que PostgreSQL esté listo
# ============================================

log_info "Esperando a que PostgreSQL esté disponible en $PGHOST:5432..."

MAX_RETRIES=30
RETRY_COUNT=0
PG_READY=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if pg_isready -h "$PGHOST" -p 5432 -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; then
        PG_READY=1
        log_success "PostgreSQL está listo"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log_warn "Intento $RETRY_COUNT/$MAX_RETRIES - PostgreSQL no responde, reintentando en 5 segundos..."
    sleep 5
done

if [ $PG_READY -eq 0 ]; then
    log_error "PostgreSQL no está disponible después de $MAX_RETRIES intentos"
    exit 1
fi

# ============================================
# Instalación de dependencias Python
# ============================================

log_info "Verificando dependencias Python..."

# Lista de paquetes requeridos
REQUIRED_PACKAGES="dropbox pyncclient nextcloud-api-wrapper boto3 paramiko tu-ruc-python-client openpyxl xlrd xlwt psycopg2-binary python-dateutil pytz redis requests gevent"

for package in $REQUIRED_PACKAGES; do
    if ! python3 -c "import $package" 2>/dev/null; then
        log_warn "Instalando $package..."
        pip install --user --upgrade "$package" || log_error "Error instalando $package"
    fi
done

log_success "Dependencias Python verificadas"

# ============================================
# Verificación de addons
# ============================================

log_info "Verificando rutas de addons..."

ADDONS_PATHS=(
    "/mnt/extra-addons"
    "/mnt/extra-addons-customize"
    "/mnt/extra-addons-l10py"
)

for path in "${ADDONS_PATHS[@]}"; do
    if [ -d "$path" ]; then
        log_info "Directorio de addons encontrado: $path"
        # Contar módulos
        MODULE_COUNT=$(find "$path" -name "__manifest__.py" -o -name "__openerp__.py" | wc -l)
        log_info "  Módulos encontrados: $MODULE_COUNT"
    else
        log_warn "Directorio de addons no encontrado: $path"
    fi
done

# ============================================
# Configuración de Odoo
# ============================================

log_info "Configurando Odoo..."

# Crear directorio de datos si no existe
if [ ! -d "/var/lib/odoo" ]; then
    log_info "Creando directorio /var/lib/odoo"
    mkdir -p /var/lib/odoo
    chown odoo:odoo /var/lib/odoo
fi

# ============================================
# Iniciar Odoo
# ============================================

log_info "Iniciando Odoo con los siguientes parámetros:"
log_info "  Base de datos: $PGDATABASE"
log_info "  Host: $PGHOST"
log_info "  Usuario: $PGUSER"
log_info "  Parámetros adicionales: $@"

# Ejecutar Odoo con los parámetros proporcionados
exec odoo "$@"