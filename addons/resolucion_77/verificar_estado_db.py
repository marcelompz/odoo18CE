#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación del estado de la columna resolucion_77_line_id
en la tabla account_move de PostgreSQL.

Uso: python3 verificar_estado_db.py
"""

import psycopg2
import sys
from datetime import datetime

def verificar_columna_resolucion_77():
    """
    Verifica si la columna resolucion_77_line_id existe en la tabla account_move
    """
    
    # Configuración de conexión - MODIFICAR SEGÚN TU CONFIGURACIÓN
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'NOMBRE_DE_TU_BASE',  # CAMBIAR POR EL NOMBRE REAL
        'user': 'odoo_user',              # CAMBIAR SI ES DIFERENTE
        'password': 'tu_password',        # CAMBIAR POR LA CONTRASEÑA REAL
        'port': '5432'
    }
    
    print("🔍 VERIFICACIÓN DE ESTADO DE LA BASE DE DATOS")
    print("=" * 50)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Conectar a la base de datos
        print("📡 Conectando a PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✅ Conexión exitosa")
        print()
        
        # Verificar si la tabla account_move existe
        print("📋 Verificando tabla account_move...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'account_move'
            );
        """)
        
        tabla_existe = cursor.fetchone()[0]
        if tabla_existe:
            print("✅ Tabla account_move existe")
        else:
            print("❌ Tabla account_move NO existe")
            return False
        print()
        
        # Verificar si la columna resolucion_77_line_id existe
        print("🔍 Verificando columna resolucion_77_line_id...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'account_move' 
            AND column_name = 'resolucion_77_line_id';
        """)
        
        columna_info = cursor.fetchone()
        
        if columna_info:
            print("✅ Columna resolucion_77_line_id EXISTE")
            print(f"   - Tipo de dato: {columna_info[1]}")
            print(f"   - Permite NULL: {columna_info[2]}")
            print(f"   - Valor por defecto: {columna_info[3]}")
        else:
            print("❌ Columna resolucion_77_line_id NO EXISTE")
            print("   ⚠️  Este es el problema reportado")
        print()
        
        # Verificar índices relacionados
        print("🔍 Verificando índices relacionados...")
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE tablename = 'account_move' 
            AND indexname LIKE '%resolucion_77%';
        """)
        
        indices = cursor.fetchall()
        if indices:
            print("✅ Índices encontrados:")
            for idx in indices:
                print(f"   - {idx[0]}")
        else:
            print("⚠️  No se encontraron índices relacionados con resolucion_77")
        print()
        
        # Verificar foreign keys
        print("🔍 Verificando foreign keys...")
        cursor.execute("""
            SELECT 
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'account_move'
            AND kcu.column_name = 'resolucion_77_line_id';
        """)
        
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            print("✅ Foreign keys encontradas:")
            for fk in foreign_keys:
                print(f"   - {fk[0]}: {fk[2]} -> {fk[3]}.{fk[4]}")
        else:
            print("⚠️  No se encontraron foreign keys para resolucion_77_line_id")
        print()
        
        # Resumen final
        print("📊 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 30)
        
        if columna_info:
            print("✅ ESTADO: La columna existe correctamente")
            print("   El problema puede estar en:")
            print("   - Caché de Odoo")
            print("   - Vistas no actualizadas")
            print("   - Problema de permisos")
        else:
            print("❌ ESTADO: La columna NO existe")
            print("   SOLUCIÓN REQUERIDA:")
            print("   1. Actualizar el módulo resolucion_77")
            print("   2. Ejecutar migración de base de datos")
            print("   3. Reiniciar servicio Odoo")
        
        print()
        print("💡 PRÓXIMOS PASOS:")
        if columna_info:
            print("   - Limpiar caché de Odoo")
            print("   - Actualizar vistas desde interfaz web")
            print("   - Reiniciar servicio Odoo")
        else:
            print("   - Ejecutar: ./odoo-bin -d NOMBRE_DE_TU_BASE -u resolucion_77 --stop-after-init")
            print("   - Reiniciar servicio Odoo")
            print("   - Verificar logs de migración")
        
        cursor.close()
        conn.close()
        print()
        print("✅ Verificación completada")
        
    except psycopg2.Error as e:
        print(f"❌ Error de PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando verificación de estado de la base de datos...")
    print()
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Uso: python3 verificar_estado_db.py")
        print()
        print("Este script verifica el estado de la columna resolucion_77_line_id")
        print("en la tabla account_move de PostgreSQL.")
        print()
        print("IMPORTANTE: Modificar las credenciales de conexión en el script")
        print("antes de ejecutarlo.")
        sys.exit(0)
    
    verificar_columna_resolucion_77() 