# 🚨 ERROR: column account_move.resolucion_77_line_id does not exist

## 📋 Descripción del Problema

Este error ocurre cuando el módulo `resolucion_77` está instalado pero la columna `resolucion_77_line_id` no se ha creado físicamente en la tabla `account_move` de PostgreSQL.

### 🔍 Síntomas
- Error al acceder a asientos contables
- Mensaje: `psycopg2.errors.UndefinedColumn: column account_move.resolucion_77_line_id does not exist`
- El módulo aparece instalado pero no funciona correctamente

### ✅ Verificación del Código
El campo está correctamente definido en:
- ✅ `models/account_move.py` (líneas 9-11)
- ✅ `models/__init__.py` (línea 5)
- ✅ `__init__.py` (línea 3)
- ✅ `__manifest__.py` (línea 35)

## 🚀 SOLUCIONES DISPONIBLES

### 📍 SOLUCIÓN AUTOMÁTICA (Recomendada)

**Usar el script automatizado:**

```bash
# Navegar al directorio del módulo
cd /odoo18/custom/addons/resolucion_77

# Ejecutar el script de solución
./fix_resolucion_77.sh

# O con parámetros específicos
./fix_resolucion_77.sh NOMBRE_BASE_DATOS /ruta/a/odoo18
```

**El script realizará automáticamente:**
1. ✅ Backup de la base de datos
2. ✅ Detención del servicio Odoo
3. ✅ Actualización del módulo
4. ✅ Reinicio del servicio
5. ✅ Limpieza de caché
6. ✅ Verificación de la solución

### 📍 SOLUCIÓN MANUAL PASO A PASO

#### Paso 1: Backup de la Base de Datos
```bash
pg_dump -h localhost -U odoo_user -d NOMBRE_DE_TU_BASE > backup_antes_fix_$(date +%Y%m%d_%H%M%S).sql
```

#### Paso 2: Actualizar el Módulo
```bash
# Navegar al directorio de Odoo
cd /ruta/a/tu/odoo18

# Actualizar específicamente el módulo
./odoo-bin -d NOMBRE_DE_TU_BASE -u resolucion_77 --stop-after-init

# O actualizar todos los módulos si hay dependencias
./odoo-bin -d NOMBRE_DE_TU_BASE --update=all --stop-after-init
```

#### Paso 3: Reiniciar el Servicio
```bash
sudo systemctl restart odoo18.service
sudo systemctl status odoo18.service
```

#### Paso 4: Limpiar Caché
```bash
# Opción A: Desde consola
./odoo-bin -d NOMBRE_DE_TU_BASE --load=web,web_assets --stop-after-init

# Opción B: Desde interfaz web (como admin)
# Configuración → Técnico → Vistas → Actualizar Vistas
```

#### Paso 5: Verificar la Solución
```sql
-- Conectar a PostgreSQL
psql -h localhost -U odoo_user -d NOMBRE_DE_TU_BASE

-- Verificar que la columna existe
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'account_move' 
AND column_name = 'resolucion_77_line_id';
```

## 🔧 HERRAMIENTAS DE DIAGNÓSTICO

### 📍 Script de Verificación
```bash
# Verificar el estado actual de la base de datos
python3 verificar_estado_db.py
```

**Nota:** Modificar las credenciales de conexión en el script antes de ejecutarlo.

### 📍 Verificación Manual en PostgreSQL
```sql
-- Verificar estructura de la tabla
\d account_move

-- Verificar columnas específicas
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'account_move' 
AND column_name LIKE '%resolucion%';

-- Verificar índices
SELECT indexname, indexdef
FROM pg_indexes 
WHERE tablename = 'account_move' 
AND indexname LIKE '%resolucion%';
```

## 🔄 ALTERNATIVAS SI LA SOLUCIÓN PRINCIPAL FALLA

### 📍 ALTERNATIVA A: Reinstalación Completa
```bash
# Desinstalar el módulo
./odoo-bin -d NOMBRE_DE_TU_BASE -u resolucion_77 --stop-after-init

# Reinstalar el módulo
./odoo-bin -d NOMBRE_DE_TU_BASE -i resolucion_77 --stop-after-init
```

### 📍 ALTERNATIVA B: Actualización Manual de Base de Datos
```sql
-- SOLO COMO ÚLTIMO RECURSO Y CON EXTREMO CUIDADO
-- Agregar la columna manualmente
ALTER TABLE account_move 
ADD COLUMN resolucion_77_line_id integer;

-- Crear índice
CREATE INDEX account_move_resolucion_77_line_id_idx 
ON account_move(resolucion_77_line_id);

-- Crear foreign key
ALTER TABLE account_move 
ADD CONSTRAINT account_move_resolucion_77_line_id_fkey 
FOREIGN KEY (resolucion_77_line_id) 
REFERENCES resolucion_77_line(id) ON DELETE SET NULL;
```

## 📊 LOGS Y DIAGNÓSTICO

### 📍 Logs de Odoo
```bash
# Ver logs en tiempo real
tail -f /var/log/odoo/odoo.log

# Buscar errores específicos
grep -i "resolucion_77" /var/log/odoo/odoo.log
grep -i "account_move" /var/log/odoo/odoo.log
```

### 📍 Logs de PostgreSQL
```bash
# Ver logs de PostgreSQL
tail -f /var/log/postgresql/postgresql-*.log

# Buscar errores de columna
grep -i "undefinedcolumn" /var/log/postgresql/postgresql-*.log
```

## ⚠️ PREVENCIÓN FUTURA

### 📍 Para Desarrolladores
1. **Siempre ejecutar actualizaciones completas** después de cambios en modelos
2. **Verificar migraciones** antes de desplegar en producción
3. **Usar `--stop-after-init`** para actualizaciones controladas
4. **Probar en ambiente de desarrollo** antes de producción

### 📍 Para Administradores
1. **Hacer backups regulares** antes de actualizaciones
2. **Monitorear logs** durante actualizaciones
3. **Verificar integridad** después de actualizaciones
4. **Documentar cambios** en la base de datos

## 📞 SOPORTE TÉCNICO

### 📍 Información Necesaria para Soporte
- Logs de error completos
- Versión de Odoo
- Versión del módulo resolucion_77
- Pasos exactos que causaron el error
- Resultado del script de verificación

### 📍 Contacto
- **Desarrollador:** Valente Systems EAS – Cristhel Valente
- **Email:** soporte@valentesystems.com
- **Website:** https://www.valentesystems.com

---

## 📝 NOTAS IMPORTANTES

1. **Siempre hacer backup** antes de cualquier operación
2. **Probar en desarrollo** antes de aplicar en producción
3. **Documentar cambios** para futuras referencias
4. **Mantener logs** para diagnóstico de problemas

---

**Última actualización:** $(date +%Y-%m-%d)
**Versión del módulo:** 18.0.1.0.0 