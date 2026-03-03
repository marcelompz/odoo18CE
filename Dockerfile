FROM odoo:18.0

LABEL maintainer="Crossnexion EAS <contacto@crossnexion.com>"

# Cambiar a root para instalación de paquetes
USER root

# Instalar herramientas útiles y dependencias
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        ca-certificates \
        iputils-ping \
        vim-tiny \
        less \
        jq \
        && \
    rm -rf /var/lib/apt/lists/*

# Instalar paquetes Python requeridos
RUN pip install --upgrade --ignore-installed pip && \
    pip install --ignore-installed \
        dropbox \
        pyncclient \
        nextcloud-api-wrapper \
        boto3 \
        paramiko \
        tu-ruc-python-client \
        openpyxl \
        xlrd \
        xlwt \
        psycopg2-binary \
        python-dateutil \
        pytz \
        redis \
        requests \
        gevent

# Crear directorio para scripts personalizados
RUN mkdir -p /opt/odoo/custom_scripts && \
    chown -R odoo:odoo /opt/odoo/custom_scripts

# Copiar entrypoint script mejorado
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown odoo:odoo /entrypoint.sh

# Volver al usuario odoo
USER odoo

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

# Expose puerto de longpolling
EXPOSE 8072

# Entrypoint personalizado
ENTRYPOINT ["/entrypoint.sh"]
