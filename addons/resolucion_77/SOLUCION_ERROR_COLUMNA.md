# 🔧 SOLUCIÓN AL ERROR: column account_move.resolucion_77_line_id does not exist

## 📋 Diagnóstico del Problema

El error indica que la columna `resolucion_77_line_id` no existe en la tabla `account_move` de PostgreSQL, aunque está correctamente definida en el código Python del módulo `resolucion_77`.

### ✅ Verificación del Código
- ✅ Campo definido en: `models/account_move.py` (línea 9-11)
- ✅ Modelo importado en: `models/__init__.py` (línea 5)
- ✅ Módulo importado en: `__init__.py` (línea 3)
- ✅ Dependencias correctas en: `__manifest__.py` (línea 35)

## 🚀 SOLUCIÓN PASO A PASO

### 📍 PASO 1: Backup de la Base de Datos (OBLIGATORIO)
```bash
# Crear backup antes de cualquier operación
pg_dump -h localhost -U odoo_user -d NOMBRE_DE_TU_BASE > backup_antes_fix_$(date +%Y%m%d_%H%M%S).sql
```

### 📍 PASO 2: Actualización Completa del Módulo
```bash
# Navegar al directorio de Odoo
cd /ruta/a/tu/odoo18

# Actualizar específicamente el módulo resolucion_77
./odoo-bin -d NOMBRE_DE_TU_BASE -u resolucion_77 --stop-after-init

# O actualizar todos los módulos si hay dependencias
./odoo-bin -d NOMBRE_DE_TU_BASE --update=all --stop-after-init
```

### 📍 PASO 3: Reiniciar el Servicio Odoo
```bash
# Reiniciar el servicio
sudo systemctl restart odoo18.service

# Verificar que el servicio esté funcionando
sudo systemctl status odoo18.service
```

### 📍 PASO 4: Limpiar Caché y Actualizar Vistas
```bash
# Opción A: Desde consola
./odoo-bin -d NOMBRE_DE_TU_BASE --load=web,web_assets --stop-after-init

# Opción B: Desde interfaz web (como admin)
# Configuración → Técnico → Vistas → Actualizar Vistas
```

### 📍 PASO 5: Verificación de la Solución
```sql
-- Conectar a PostgreSQL y verificar que la columna existe
psql -h localhost -U odoo_user -d NOMBRE_DE_TU_BASE

-- Verificar la existencia de la columna
\d account_move

-- O consultar específicamente la columna
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'account_move' 
AND column_name = 'resolucion_77_line_id';
```

## 🔄 ALTERNATIVAS SI LA SOLUCIÓN PRINCIPAL FALLA

### 📍 ALTERNATIVA A: Reinstalación Limpia del Módulo
```bash
# Desinstalar el módulo
./odoo-bin -d NOMBRE_DE_TU_BASE -u resolucion_77 --stop-after-init

# Reinstalar el módulo
./odoo-bin -d NOMBRE_DE_TU_BASE -i resolucion_77 --stop-after-init
```

### 📍 ALTERNATIVA B: Actualización Manual de la Base de Datos
```sql
-- SOLO SI ES NECESARIO Y CON EXTREMO CUIDADO
-- Agregar la columna manualmente (último recurso)
ALTER TABLE account_move 
ADD COLUMN resolucion_77_line_id integer;

-- Crear el índice y la foreign key
CREATE INDEX account_move_resolucion_77_line_id_idx 
ON account_move(resolucion_77_line_id);

ALTER TABLE account_move 
ADD CONSTRAINT account_move_resolucion_77_line_id_fkey 
FOREIGN KEY (resolucion_77_line_id) 
REFERENCES resolucion_77_line(id) ON DELETE SET NULL;
```

## ⚠️ PREVENCIÓN FUTURA

### 📍 Para Desarrolladores:
1. **Siempre ejecutar actualizaciones completas** después de cambios en modelos
2. **Verificar migraciones** antes de desplegar en producción
3. **Usar `--stop-after-init`** para actualizaciones controladas

### 📍 Para Administradores:
1. **Hacer backups regulares** antes de actualizaciones
2. **Probar en ambiente de desarrollo** antes de producción
3. **Monitorear logs** durante actualizaciones

## 📞 SOPORTE TÉCNICO

Si el problema persiste después de seguir estos pasos:

1. **Revisar logs de Odoo**: `/var/log/odoo/odoo.log`
2. **Verificar logs de PostgreSQL**: `/var/log/postgresql/`
3. **Contactar al equipo de desarrollo** con:
   - Logs de error completos
   - Versión de Odoo
   - Versión del módulo resolucion_77
   - Pasos exactos que causaron el error

---

**⚠️ IMPORTANTE**: Este documento debe ser actualizado cada vez que se modifique la estructura del módulo para evitar futuros problemas de migración. 