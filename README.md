# Odoo 18 CE - Configuración Docker Compose Optimizada

## 📋 Resumen

Configuración optimizada de Docker Compose para Odoo 18 CE basada en la auditoría de `odoo9049`. Esta configuración incluye mejores prácticas, health checks, redes definidas y configuración de performance optimizada.

## 🚀 Mejoras Implementadas

### 1. **Docker Compose (`docker-compose.yml`)**
- **Health checks** para ambos servicios (web y db)
- **Red dedicada** con subnet configurable
- **Dependencias con condiciones** (`condition: service_healthy`)
- **Build context explícito** con dockerfile específico
- **Puerto longpolling** expuesto (8072)
- **Restart policies** optimizadas (`unless-stopped` para web, `always` para db)
- **Volúmenes read-only** para configuración
- **Variables de entorno PostgreSQL** completas

### 2. **Variables de Entorno (`.env`)**
- **Configuración organizada** por secciones
- **Passwords seguras** por defecto
- **Configuración de PostgreSQL optimizada** (encoding, collation)
- **Parámetros de performance** para Odoo
- **Timezone configurable** con valor por defecto
- **Subnet de red configurable**

### 3. **Dockerfile Optimizado**
- **Health check integrado** en la imagen
- **Herramientas de debugging** incluidas (curl, vim-tiny, jq)
- **Dependencias Python** pre-instaladas
- **Entrypoint personalizado** mejorado
- **Usuario seguro** (odoo)
- **Directorio para scripts personalizados**

### 4. **Entrypoint Mejorado (`entrypoint.sh`)**
- **Logs con colores** para mejor legibilidad
- **Validación de variables** críticas
- **Espera inteligente** para PostgreSQL
- **Verificación de dependencias** Python
- **Detección de addons** automática
- **Manejo de errores** robusto

### 5. **Configuración de Odoo (`config/odoo.conf`)**
- **Performance optimizada** (workers, límites de memoria)
- **Logging configurado** para producción
- **Seguridad mejorada** (unaccent habilitado)
- **Configuración de longpolling** correcta
- **Addons paths** verificados
- **Parámetros de cron** optimizados

## 🔍 Comparación con configuración original

| Característica | Configuración original | Configuración optimizada |
|----------------|----------|----------------------|
| Health checks | ❌ No tiene | ✅ Incluidos para web y db |
| Red dedicada | ❌ Default network | ✅ Red bridge con subnet configurable |
| Espera PostgreSQL | ❌ Básica | ✅ Inteligente con reintentos |
| Logging | ❌ Básico | ✅ Con colores y niveles |
| Performance | ⚠️ Configuración básica | ✅ Optimizada (workers, límites) |
| Seguridad | ⚠️ Passwords en texto | ✅ Passwords seguras por defecto |
| Variables de entorno | ⚠️ Desorganizadas | ✅ Organizadas y documentadas |
| Entrypoint | ⚠️ Script simple | ✅ Robust con validaciones |

## 🛠️ Uso

### 1. Iniciar los servicios
```bash
cd /opt/odoo/odoo18-docker-compose
docker compose up -d
```

### 2. Ver logs
```bash
docker compose logs -f
```

### 3. Verificar estado
```bash
docker compose ps
```

### 4. Acceder a Odoo
- **URL:** http://localhost:8069
- **Usuario:** admin
- **Contraseña:** soporte.159753

### 5. Configurar passwords personalizados
Editar el archivo `.env` antes de iniciar:
```bash
cp .env .env.local
# Editar .env.local con tus valores
docker compose --env-file .env.local up -d
```

## ⚙️ Personalización

### Variables principales en `.env`
- `WEB_PORT`: Puerto para Odoo (9090)
- `DB_PORT`: Puerto para PostgreSQL (9091)
- `DB_PASSWD`: Password de PostgreSQL
- `WEB_ADDONS_CUSTOMIZE`: Ruta a addons personalizados
- `WEB_ADDONS_L10NPY`: Ruta a localización PY
- `TZ`: Zona horaria

### Configuración de performance
Ajustar en `config/odoo.conf`:
- `workers`: Número de workers (recomendado: CPU cores * 2 + 1)
- `limit_memory_hard`: Límite máximo de memoria
- `limit_request`: Tamaño máximo de request

## 🐛 Troubleshooting

### 1. PostgreSQL no inicia
```bash
# Verificar logs de PostgreSQL
docker compose logs db9090

# Verificar permisos de volumen
sudo chown -R 999:999 /home/docker/odoo9090/db-data
```

### 2. Odoo no se conecta a PostgreSQL
```bash
# Verificar health check
docker compose ps

# Probar conexión manualmente
docker compose exec db9090 pg_isready -U odoo -d odoo_prod_9090
```

### 3. Addons no se cargan
```bash
# Verificar rutas en entrypoint
docker compose logs web9090 | grep "Directorio de addons"

# Verificar permisos
ls -la /opt/odoo/odoo9090/addons/
```

## 📊 Monitoreo

### Health checks automáticos
```bash
# Verificar health status
docker inspect --format='{{.State.Health.Status}}' odoo_web_9090
docker inspect --format='{{.State.Health.Status}}' db_odoo_9090
```

### Métricas básicas
```bash
# Uso de recursos
docker stats odoo_web_9090 db_odoo_9090

# Logs en tiempo real
docker compose logs -f --tail=100
```

## 🤝 Contribución

Esta configuración es un punto de partida. Para personalizaciones específicas:

1. Modificar `.env` para ajustar variables
2. Ajustar `config/odoo.conf` para parámetros de Odoo
3. Extender `Dockerfile` para dependencias adicionales
4. Personalizar `entrypoint.sh` para lógica de inicialización

## 📄 Licencia

Configuración desarrollada por Crossnexion EAS para uso interno y compartido bajo mejores prácticas de Docker y Odoo.

---
*Última actualización: $(date)*