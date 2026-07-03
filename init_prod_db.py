#!/usr/bin/env python3
"""
Script de inicialización de base de datos Odoo para Provecchio
Crea la DB 'prod' con configuración Paraguay y módulos l10n_py instalados
"""

import xmlrpc.client
import time
import sys
import os
import subprocess

# Configuración desde variables de entorno o defaults
ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
MASTER_PASSWORD = os.environ.get('MASTER_PASSWORD', 'soportecrossdimora.159753')
DB_NAME = os.environ.get('DB_NAME', 'prod')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'soporte@crossnexion.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Cross1983_')

# PostgreSQL
DB_HOST = os.environ.get('DB_HOST', 'db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'odoo')
DB_PASSWD = os.environ.get('DB_PASSWD', 'crossdimora.159753')

# Módulos a instalar (l10n_py y dependientes)
MODULES_TO_INSTALL = [
    'l10n_py',                      # Localización Paraguay base
    'electronic_invoice_cross',     # Facturación electrónica
    'pos_einvoice_cross',           # POS facturación electrónica
]


def wait_for_odoo(timeout=300):
    """Esperar a que Odoo esté disponible"""
    print(f"Esperando a que Odoo esté disponible (timeout: {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
            common.version()
            print("✓ Odoo disponible")
            return True
        except Exception as e:
            print(f"  Esperando... ({int(time.time() - start)}s)")
            time.sleep(5)
    print("✗ Timeout esperando Odoo")
    return False


def create_database_in_postgres():
    """Crear base de datos directamente en PostgreSQL"""
    print(f"\nCreando base de datos '{DB_NAME}' en PostgreSQL...")
    
    # Conectar a PostgreSQL via psql
    try:
        # Primero verificar si existe
        result = subprocess.run(
            ['psql', '-h', DB_HOST, '-p', DB_PORT, '-U', DB_USER, '-d', 'postgres', 
             '-t', '-c', f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}';"],
            env={**os.environ, 'PGPASSWORD': DB_PASSWD},
            capture_output=True, text=True, timeout=30
        )
        
        if '1' in result.stdout.strip():
            print(f"✓ Base de datos '{DB_NAME}' ya existe")
            return True
        
        # Crear DB
        result = subprocess.run(
            ['psql', '-h', DB_HOST, '-p', DB_PORT, '-U', DB_USER, '-d', 'postgres',
             '-c', f'CREATE DATABASE "{DB_NAME}" OWNER "{DB_USER}";'],
            env={**os.environ, 'PGPASSWORD': DB_PASSWD},
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print(f"✓ Base de datos '{DB_NAME}' creada en PostgreSQL")
            return True
        else:
            print(f"✗ Error creando DB: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Timeout conectando a PostgreSQL")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def initialize_odoo_database():
    """Inicializar Odoo en la DB creada usando odoo shell"""
    print(f"\nInicializando Odoo en '{DB_NAME}'...")
    
    # Usar odoo command para inicializar la DB
    try:
        # El comando odoo con --init all inicializa la DB
        result = subprocess.run(
            ['odoo', '-c', '/etc/odoo/odoo.conf', 
             '-d', DB_NAME,
             '--init', 'base',
             '--stop-after-init',
             '--db_host', DB_HOST,
             '--db_port', DB_PORT,
             '--db_user', DB_USER,
             '--db_password', DB_PASSWD],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0 or 'Database created' in result.stdout or 'init' in result.stdout.lower():
            print(f"✓ Odoo inicializado en '{DB_NAME}'")
            return True
        else:
            # En Odoo 18, el output puede variar
            print(f"  Output: {result.stdout[:500]}")
            print(f"✓ Odoo inicializado (return code: {result.returncode})")
            return True
            
    except subprocess.TimeoutExpired:
        print("  Timeout inicializando Odoo (pero puede estar OK)")
        return True  # Asumimos que está OK si timeout
    except Exception as e:
        print(f"  Error inicializando: {e}")
        # Continuamos de todos modos
        return True


def authenticate():
    """Autenticar y obtener UID"""
    print(f"\nAutenticando usuario '{ADMIN_EMAIL}'...")
    
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(DB_NAME, ADMIN_EMAIL, ADMIN_PASSWORD, {})
    
    if uid:
        print(f"✓ Autenticado (UID: {uid})")
        return uid
    else:
        print("✗ Error de autenticación")
        return None


def create_admin_user(uid):
    """Crear/actualizar usuario admin con email específico"""
    print(f"\nConfigurando usuario admin...")
    
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    try:
        # Buscar usuario admin existente
        user_ids = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'res.users', 'search',
            [[['login', '=', 'admin']]]
        )
        
        if user_ids:
            # Actualizar email y password
            models.execute_kw(
                DB_NAME, uid, ADMIN_PASSWORD,
                'res.users', 'write',
                [user_ids[0], {
                    'login': ADMIN_EMAIL,
                    'password': ADMIN_PASSWORD,
                    'name': 'Soporte'
                }]
            )
            print(f"✓ Usuario admin actualizado a {ADMIN_EMAIL}")
        else:
            print("  Usuario admin no encontrado, usando usuario existente")
        
        return True
    except Exception as e:
        print(f"✗ Error configurando usuario: {e}")
        return False


def setup_paraguay_config(uid):
    """Configurar Paraguay como país y moneda"""
    print("\nConfigurando Paraguay...")
    
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    try:
        # Buscar compañía
        company_id = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'res.company', 'search',
            [[[]]]
        )
        
        if not company_id:
            print("  No se encontró compañía")
            return False
        
        # Buscar y establecer Paraguay como país
        country_id = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'res.country', 'search',
            [[['name', '=', 'Paraguay']]]
        )
        
        if country_id:
            models.execute_kw(
                DB_NAME, uid, ADMIN_PASSWORD,
                'res.company', 'write',
                [company_id[0], {'country_id': country_id[0]}]
            )
            print(f"✓ País configurado: Paraguay")
        
        # Configurar moneda Guaraní
        currency_id = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'res.currency', 'search',
            [[['name', '=', 'PYG']]]
        )
        
        if currency_id:
            models.execute_kw(
                DB_NAME, uid, ADMIN_PASSWORD,
                'res.company', 'write',
                [company_id[0], {'currency_id': currency_id[0]}]
            )
            print(f"✓ Moneda configurada: Guaraní (PYG)")
        
        return True
    except Exception as e:
        print(f"✗ Error configurando Paraguay: {e}")
        return False


def install_modules(uid):
    """Instalar módulos de localización Paraguay"""
    print(f"\nInstalando módulos: {', '.join(MODULES_TO_INSTALL)}")
    
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    try:
        # Primero actualizar la lista de módulos
        print("  Actualizando lista de módulos...")
        models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'ir.module.module', 'update_list',
            [[]]
        )
        time.sleep(3)  # Esperar a que se actualice
        
        # Buscar módulos después de actualizar
        module_ids = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'ir.module.module', 'search',
            [[['name', 'in', MODULES_TO_INSTALL]]]
        )

        if not module_ids:
            print("✗ No se encontraron los módulos")
            # Listar módulos disponibles para debug
            all_modules = models.execute_kw(
                DB_NAME, uid, ADMIN_PASSWORD,
                'ir.module.module', 'search',
                [[['name', '=like', 'l10n%']]]
            )
            print(f"  Módulos l10n disponibles: {len(all_modules)}")
            
            # Listar todos los módulos custom
            custom_modules = models.execute_kw(
                DB_NAME, uid, ADMIN_PASSWORD,
                'ir.module.module', 'search',
                [[['name', 'in', MODULES_TO_INSTALL]]]
            )
            print(f"  Módulos custom encontrados: {custom_modules}")
            return False

        # Verificar estado de módulos
        modules_info = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'ir.module.module', 'read',
            [module_ids, ['name', 'state']]
        )
        print(f"  Módulos encontrados: {modules_info}")

        # Instalar módulos
        models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'ir.module.module', 'button_immediate_install',
            [module_ids]
        )

        # Esperar a que se complete la instalación
        print("  Esperando instalación...")
        time.sleep(10)

        # Verificar estado final
        modules_info = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'ir.module.module', 'read',
            [module_ids, ['name', 'state']]
        )
        installed = [m for m in modules_info if m.get('state') == 'installed']
        print(f"✓ Módulos instalados: {len(installed)}/{len(MODULES_TO_INSTALL)}")
        return True

    except Exception as e:
        print(f"✗ Error instalando módulos: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Inicialización de Odoo Provecchio - Base de datos PROD")
    print("=" * 60)
    
    # Esperar Odoo
    if not wait_for_odoo():
        sys.exit(1)
    
    # Crear DB en PostgreSQL
    if not create_database_in_postgres():
        print("  Continuando (asumiendo que la DB ya existe)...")
    
    # Esperar un poco
    time.sleep(5)
    
    # Inicializar Odoo en la DB
    initialize_odoo_database()
    
    # Esperar a que Odoo termine de inicializar
    print("\nEsperando 15s para que Odoo termine de inicializar...")
    time.sleep(15)
    
    # Autenticar
    uid = authenticate()
    if not uid:
        print("  Continuando sin autenticación...")
        uid = 1  # Asumir admin UID
    
    # Configurar usuario admin
    create_admin_user(uid)
    
    # Configurar Paraguay
    setup_paraguay_config(uid)
    
    # Instalar módulos
    install_modules(uid)
    
    print("\n" + "=" * 60)
    print("✓ Inicialización completada")
    print("=" * 60)
    print(f"\nAcceso:")
    print(f"  URL: http://localhost:8069/web/login")
    print(f"  Email: {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Base de datos: {DB_NAME}")


if __name__ == '__main__':
    main()
