#!/usr/bin/env python3
"""
Script de inicialización de base de datos Odoo para Provecchio
Crea la DB 'prod' con configuración Paraguay y módulos l10n_py instalados
"""

import xmlrpc.client
import time
import sys
import os

# Configuración desde variables de entorno o defaults
ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
MASTER_PASSWORD = os.environ.get('MASTER_PASSWORD', 'soportecrossdimora.159753')
DB_NAME = os.environ.get('DB_NAME', 'prod')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'soporte@crossnexion.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Cross1983_')
COUNTRY = 'Paraguay'
LANGUAGE = 'es_PY'

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


def create_database():
    """Crear base de datos"""
    print(f"\nCreando base de datos '{DB_NAME}'...")
    
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    
    # Verificar si ya existe
    try:
        db_list = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db')
        existing_dbs = db_list.list()
        if DB_NAME in existing_dbs:
            print(f"✓ Base de datos '{DB_NAME}' ya existe")
            return True
    except Exception as e:
        print(f"Error verificando DB: {e}")
    
    # Crear DB
    try:
        db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db')
        db.create_database(
            MASTER_PASSWORD,
            DB_NAME,
            True,  # demo=False
            'es_PY',  # language
            ADMIN_PASSWORD,  # admin password
            'Soporte',  # name
            ADMIN_EMAIL,  # email
            1  # user_id
        )
        print(f"✓ Base de datos '{DB_NAME}' creada")
        return True
    except Exception as e:
        print(f"✗ Error creando DB: {e}")
        return False


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


def setup_paraguay_config(uid):
    """Configurar Paraguay como país y moneda"""
    print("\nConfigurando Paraguay...")
    
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    try:
        # Buscar y establecer Paraguay como país
        country_id = models.execute_kw(
            DB_NAME, uid, ADMIN_PASSWORD,
            'res.country', 'search',
            [[['name', '=', 'Paraguay']]]
        )
        
        if country_id:
            # Actualizar compañía con país Paraguay
            company_id = models.execute_kw(
                DB_NAME, uid, ADMIN_PASSWORD,
                'res.company', 'search',
                [[[]]]
            )
            
            if company_id:
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
        time.sleep(2)  # Esperar a que se actualice
        
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
        time.sleep(5)

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
    
    # Crear DB
    if not create_database():
        sys.exit(1)
    
    # Esperar un poco para que la DB esté lista
    print("\nEsperando 10s para que la DB esté lista...")
    time.sleep(10)
    
    # Autenticar
    uid = authenticate()
    if not uid:
        sys.exit(1)
    
    # Configurar Paraguay
    setup_paraguay_config(uid)
    
    # Instalar módulos
    install_modules(uid)
    
    print("\n" + "=" * 60)
    print("✓ Inicialización completada")
    print("=" * 60)
    print(f"\nAcceso:")
    print(f"  URL: {ODOO_URL}/web/login")
    print(f"  Email: {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Base de datos: {DB_NAME}")


if __name__ == '__main__':
    main()
