FROM odoo:18.0

USER root

LABEL MAINTAINER="Provecchio Di Mora <soporte@provecchio.com>"
LABEL DESCRIPTION="Odoo 18.0 CE - Optimized for Provecchio Di Mora"

# Instalar herramientas de debugging y utilidades
RUN apt-get update && apt-get install -y \
    curl \
    vim-tiny \
    jq \
    netcat-openbsd \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar entrypoint mejorado
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Crear directorio para scripts personalizados
RUN mkdir -p /opt/odoo/custom-scripts && chown odoo:odoo /opt/odoo/custom-scripts

# Health check integrado
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

USER odoo

# Puerto principal y longpolling
EXPOSE 8069 8072

ENTRYPOINT ["/entrypoint.sh"]
