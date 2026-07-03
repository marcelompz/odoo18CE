#!/bin/bash

# ===========================================
# ODOO 18 CE - ENTRYPOINT MEJORADO
# Provecchio Di Mora
# ===========================================

set -e

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===========================================
# 1. VALIDACIÓN DE VARIABLES CRÍTICAS
# ===========================================
log_info "Validando variables de entorno..."

if [ -z "$HOST" ]; then
    log_error "HOST no está definido. Usando 'db' por defecto."
    export HOST="db"
fi

if [ -z "$USER" ]; then
    log_error "USER no está definido. Usando 'odoo' por defecto."
    export USER="odoo"
fi

if [ -z "$PASSWORD" ]; then
    log_error "PASSWORD no está definido."
    exit 1
fi

log_success "Variables validadas: HOST=$HOST, USER=$USER"

# ===========================================
# 2. ESPERA INTELIGENTE PARA POSTGRESQL
# ===========================================
log_info "Esperando a PostgreSQL..."

max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if nc -z "$HOST" 5432 2>/dev/null; then
        log_success "PostgreSQL está listo (intento $attempt/$max_attempts)"
        break
    else
        log_info "Esperando PostgreSQL... (intento $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    log_error "PostgreSQL no respondió después de $max_attempts intentos"
    exit 1
fi

# ===========================================
# 3. VERIFICAR DEPENDENCIAS PYTHON
# ===========================================
log_info "Verificando dependencias Python..."

if [ -f /tmp/requirements.txt ]; then
    log_info "Instalando dependencias desde requirements.txt..."
    pip install --break-system-packages -r /tmp/requirements.txt || log_warning "Algunas dependencias fallaron"
fi

# ===========================================
# 4. DETECCIÓN DE ADDONS PERSONALIZADOS
# ===========================================
log_info "Detectando addons personalizados..."

if [ -d "/mnt/extra-addons-customize" ]; then
    addon_count=$(find /mnt/extra-addons-customize -maxdepth 2 -name "__manifest__.py" | wc -l)
    log_success "Encontrados $addon_count módulos personalizados"
else
    log_warning "Directorio de addons personalizados no encontrado"
fi

# ===========================================
# 5. CONFIGURAR PARÁMETROS DE PERFORMANCE
# ===========================================
log_info "Configurando parámetros de performance..."

# Configurar workers si está definido
if [ -n "$ODOO_WORKERS" ]; then
    export ODOO_WORKERS
    log_info "Workers configurados: $ODOO_WORKERS"
fi

# Configurar límites de memoria
if [ -n "$ODOO_LIMIT_MEMORY_HARD" ]; then
    export ODOO_LIMIT_MEMORY_HARD
    log_info "Límite de memoria: $ODOO_LIMIT_MEMORY_HARD bytes"
fi

# ===========================================
# 6. INICIAR ODOO
# ===========================================
log_success "Iniciando Odoo 18.0 CE..."
log_info "Conectando a PostgreSQL en $HOST:5432"

exec odoo --config /etc/odoo/odoo.conf "$@"
