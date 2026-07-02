#!/bin/bash

# Script para solucionar el error de la columna resolucion_77_line_id
# Uso: ./fix_resolucion_77.sh [NOMBRE_BASE_DATOS] [RUTA_ODOO]

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para mostrar ayuda
show_help() {
    echo "Script para solucionar el error de la columna resolucion_77_line_id"
    echo ""
    echo "Uso: $0 [NOMBRE_BASE_DATOS] [RUTA_ODOO]"
    echo ""
    echo "Argumentos:"
    echo "  NOMBRE_BASE_DATOS    Nombre de la base de datos (opcional)"
    echo "  RUTA_ODOO           Ruta al directorio de Odoo (opcional)"
    echo ""
    echo "Ejemplos:"
    echo "  $0"
    echo "  $0 mi_base_datos"
    echo "  $0 mi_base_datos /opt/odoo18"
    echo ""
    echo "Si no se proporcionan argumentos, el script pedirá la información."
}

# Verificar si se solicita ayuda
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Configuración
DATABASE_NAME="${1:-}"
ODOO_PATH="${2:-}"

# Obtener configuración si no se proporcionó
if [[ -z "$DATABASE_NAME" ]]; then
    echo -n "Ingrese el nombre de la base de datos: "
    read DATABASE_NAME
fi

if [[ -z "$ODOO_PATH" ]]; then
    echo -n "Ingrese la ruta al directorio de Odoo (ej: /opt/odoo18): "
    read ODOO_PATH
fi

# Validar que la ruta de Odoo existe
if [[ ! -d "$ODOO_PATH" ]]; then
    print_error "La ruta de Odoo no existe: $ODOO_PATH"
    exit 1
fi

# Validar que existe odoo-bin
if [[ ! -f "$ODOO_PATH/odoo-bin" ]]; then
    print_error "No se encontró odoo-bin en: $ODOO_PATH"
    exit 1
fi

print_status "Iniciando solución para el error de resolucion_77_line_id"
print_status "Base de datos: $DATABASE_NAME"
print_status "Ruta Odoo: $ODOO_PATH"
echo ""

# Función para crear backup
create_backup() {
    print_status "Creando backup de la base de datos..."
    
    BACKUP_FILE="backup_${DATABASE_NAME}_$(date +%Y%m%d_%H%M%S).sql"
    
    if pg_dump -h localhost -U odoo_user -d "$DATABASE_NAME" > "$BACKUP_FILE" 2>/dev/null; then
        print_success "Backup creado: $BACKUP_FILE"
    else
        print_warning "No se pudo crear backup automático. Continuando..."
        print_warning "Se recomienda crear backup manual antes de continuar."
        echo -n "¿Desea continuar sin backup? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_error "Operación cancelada por el usuario"
            exit 1
        fi
    fi
    echo ""
}

# Función para verificar si el servicio Odoo está corriendo
check_odoo_service() {
    print_status "Verificando estado del servicio Odoo..."
    
    if systemctl is-active --quiet odoo18.service; then
        print_warning "El servicio Odoo está corriendo. Se detendrá temporalmente."
        echo -n "¿Desea continuar? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_error "Operación cancelada por el usuario"
            exit 1
        fi
        
        print_status "Deteniendo servicio Odoo..."
        sudo systemctl stop odoo18.service
        sleep 2
    else
        print_success "Servicio Odoo no está corriendo"
    fi
    echo ""
}

# Función para actualizar el módulo
update_module() {
    print_status "Actualizando módulo resolucion_77..."
    
    cd "$ODOO_PATH"
    
    if ./odoo-bin -d "$DATABASE_NAME" -u resolucion_77 --stop-after-init; then
        print_success "Módulo resolucion_77 actualizado correctamente"
    else
        print_error "Error al actualizar el módulo resolucion_77"
        print_status "Intentando actualización completa..."
        
        if ./odoo-bin -d "$DATABASE_NAME" --update=all --stop-after-init; then
            print_success "Actualización completa realizada"
        else
            print_error "Error en la actualización completa"
            return 1
        fi
    fi
    echo ""
}

# Función para reiniciar el servicio
restart_service() {
    print_status "Reiniciando servicio Odoo..."
    
    if sudo systemctl restart odoo18.service; then
        print_success "Servicio Odoo reiniciado correctamente"
    else
        print_error "Error al reiniciar el servicio Odoo"
        return 1
    fi
    
    # Esperar a que el servicio esté listo
    print_status "Esperando a que el servicio esté listo..."
    sleep 5
    
    if systemctl is-active --quiet odoo18.service; then
        print_success "Servicio Odoo está funcionando correctamente"
    else
        print_error "El servicio Odoo no está funcionando"
        return 1
    fi
    echo ""
}

# Función para limpiar caché
clear_cache() {
    print_status "Limpiando caché de Odoo..."
    
    cd "$ODOO_PATH"
    
    if ./odoo-bin -d "$DATABASE_NAME" --load=web,web_assets --stop-after-init; then
        print_success "Caché limpiado correctamente"
    else
        print_warning "No se pudo limpiar el caché automáticamente"
        print_warning "Se recomienda limpiar el caché desde la interfaz web"
    fi
    echo ""
}

# Función para verificar la solución
verify_solution() {
    print_status "Verificando la solución..."
    
    # Verificar si la columna existe
    if psql -h localhost -U odoo_user -d "$DATABASE_NAME" -c "
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'account_move' 
        AND column_name = 'resolucion_77_line_id';
    " 2>/dev/null | grep -q "resolucion_77_line_id"; then
        print_success "✅ La columna resolucion_77_line_id existe en la base de datos"
        return 0
    else
        print_error "❌ La columna resolucion_77_line_id NO existe en la base de datos"
        return 1
    fi
}

# Función principal
main() {
    echo "=========================================="
    echo "🔧 SOLUCIONADOR DE ERROR RESOLUCIÓN 77"
    echo "=========================================="
    echo ""
    
    # Paso 1: Crear backup
    create_backup
    
    # Paso 2: Verificar servicio
    check_odoo_service
    
    # Paso 3: Actualizar módulo
    if ! update_module; then
        print_error "Falló la actualización del módulo"
        print_status "Reiniciando servicio antes de salir..."
        sudo systemctl start odoo18.service
        exit 1
    fi
    
    # Paso 4: Reiniciar servicio
    if ! restart_service; then
        print_error "Falló el reinicio del servicio"
        exit 1
    fi
    
    # Paso 5: Limpiar caché
    clear_cache
    
    # Paso 6: Verificar solución
    if verify_solution; then
        echo ""
        echo "=========================================="
        print_success "🎉 PROBLEMA SOLUCIONADO EXITOSAMENTE"
        echo "=========================================="
        echo ""
        print_status "Próximos pasos recomendados:"
        echo "  1. Acceder a Odoo y verificar que funciona correctamente"
        echo "  2. Ir a Configuración → Técnico → Vistas → Actualizar Vistas"
        echo "  3. Probar la funcionalidad del módulo resolucion_77"
        echo ""
    else
        echo ""
        echo "=========================================="
        print_error "❌ EL PROBLEMA PERSISTE"
        echo "=========================================="
        echo ""
        print_status "Pasos adicionales recomendados:"
        echo "  1. Verificar logs de Odoo: /var/log/odoo/odoo.log"
        echo "  2. Verificar logs de PostgreSQL"
        echo "  3. Considerar reinstalación completa del módulo"
        echo "  4. Contactar al equipo de desarrollo"
        echo ""
    fi
}

# Ejecutar función principal
main "$@" 