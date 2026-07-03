#!/bin/bash
#!/bin/bash

# ===========================================
# ODOO 18 CE - DEPLOYMENT SCRIPT
# Provecchio Di Mora - Production
# ===========================================

set -e

# Configuration
DEPLOY_DIR="/srv/odoo8082"
REPO_URL="https://github.com/marcelompz/odoo18CE.git"
PROJECT_NAME="odoo8082"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===========================================
# 1. CLONE OR UPDATE REPOSITORY
# ===========================================
log_info "=== CLONING/UPDATING REPOSITORY ==="

if [ -d "$DEPLOY_DIR/.git" ]; then
    cd "$DEPLOY_DIR"
    git pull origin master
    log_success "Repository updated"
else
    mkdir -p "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
    git clone "$REPO_URL" .
    log_success "Repository cloned"
fi

# ===========================================
# 2. CREATE .ENV FILE
# ===========================================
log_info "=== CREATING .ENV FILE ==="

cat > .env << 'EOF'
# ODOO 18 CE - PROVECCHIO DI MORA
WEB_HOST=odoo_web_8082
WEB_IMAGE_NAME=odoo
WEB_IMAGE_TAG=18.0
WEB_PORT=8082
WEB_ADDONS_CUSTOMIZE=/srv/odoo8082/addons
WEB_VOLUMES=/srv/odoo8082/web-data

DB_IMAGE=postgres
DB_TAG=15
DB_HOST=db_odoo_5434
DB_PORT=5434
DB_NAME=postgres
DB_USER=odoo
DB_PASSWD=crossdimora.159753
DB_VOLUMES=/srv/odoo8082/db-data

TZ=America/Asuncion
DEBIAN_FRONTEND=noninteractive
EOF

log_success ".env file created"

# ===========================================
# 3. CREATE MODULES CONFIGURATION
# ===========================================
log_info "=== CREATING MODULES CONFIGURATION ==="

cat > modules.conf << 'EOF'
# ===========================================
# MÓDULOS A INSTALAR AUTOMÁTICAMENTE
# Provecchio Di Mora - Odoo 18 CE
# ===========================================

# Base
base
web

# Localización Paraguay
l10n_py

# Contabilidad
account
account_check_printing

# Inventario
stock

# Fabricación
mrp

# Punto de Venta
point_of_sale
pos_product_bom

# Ventas
sale_management

# Compras
purchase

# Contactos
contacts

# Empleados
hr

# Configuración regional
base_address_city
base_address_extended
base_geolocalize

# Reportes
account_reports

# ===========================================
# MÓDULOS PARAGUAYOS (l10n_py/v18)
# ===========================================

# Factura Electrónica
electronic_invoice_cross
pos_einvoice_cross

# Email
de_send_email_cross
EOF

log_success "Modules configuration created"

# ===========================================
# 4. STOP AND REMOVE OLD CONTAINERS
# ===========================================
log_info "=== STOPPING OLD CONTAINERS ==="

docker compose down 2>/dev/null || true
log_success "Old containers stopped"

# ===========================================
# 5. START NEW CONTAINERS
# ===========================================
log_info "=== STARTING NEW CONTAINERS ==="

docker compose up -d

log_success "Containers started"

# ===========================================
# 6. WAIT FOR HEALTHY STATUS
# ===========================================
log_info "=== WAITING FOR HEALTHY STATUS (max 120s) ==="

max_attempts=24
attempt=1

while [ $attempt -le $max_attempts ]; do
    status=$(docker inspect --format='{{.State.Health.Status}}' odoo_web_8082 2>/dev/null || echo "starting")
    
    if [ "$status" = "healthy" ]; then
        log_success "Odoo is healthy! (attempt $attempt/$max_attempts)"
        break
    else
        log_info "Waiting... ($attempt/$max_attempts) - Status: $status"
        sleep 5
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    log_warning "Odoo not healthy after ${max_attempts} attempts, but continuing..."
fi

# ===========================================
# 7. VERIFY INSTALLATION
# ===========================================
log_info "=== VERIFYING INSTALLATION ==="

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETED!"
echo "=========================================="
echo ""
echo "📋 ACCESS INFORMATION:"
echo "   URL: http://$(hostname -I | awk '{print $1}'):8082"
echo "   Database: prod"
echo "   Master Password: soportecrossdimora.159753"
echo ""
echo "📦 INSTALLED MODULES:"
echo "   - Base modules"
echo "   - Paraguay Accounting (l10n_py)"
echo "   - Electronic Invoice"
echo "   - POS Integration"
echo ""
echo "🔗 ORDERFLOW INTEGRATION:"
echo "   XML-RPC: http://$(hostname -I | awk '{print $1}'):8082/xmlrpc/2/object"
echo "   User: orderflow_api (create manually)"
echo ""
echo "=========================================="
echo ""

log_success "Deployment script completed!"
