.. image:: https://img.shields.io/badge/license-AGPL--3-blue.svg
    :target: https://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

Web Pay Shipping Methods
========================

Este módulo extiende la funcionalidad de la tienda web de Odoo para permitir la subida de comprobantes de transferencia bancaria durante el proceso de pago.

Características
--------------

* **Comprobantes de Transferencia**: Los clientes pueden subir comprobantes de transferencia bancaria durante el proceso de pago
* **Validación de Archivos**: Validación automática de tipos de archivo y tamaño máximo
* **Almacenamiento Seguro**: Los archivos se almacenan como adjuntos en la orden de venta
* **Interfaz Intuitiva**: Campo de archivo con feedback visual del estado de carga

Tipos de Archivo Permitidos
---------------------------

* PDF (.pdf)
* Imágenes: JPG, JPEG, PNG (.jpg, .jpeg, .png)
* Documentos: DOC, DOCX (.doc, .docx)
* Texto: TXT (.txt)

Límites
-------

* Tamaño máximo: 10MB por archivo
* Un archivo por orden de venta

Flujo de Trabajo
----------------

1. El cliente selecciona un método de pago por transferencia bancaria
2. Se muestra un campo opcional para subir el comprobante
3. Al seleccionar un archivo, se valida automáticamente
4. El archivo se envía al servidor y se almacena temporalmente
5. Durante la validación del pago, el archivo se adjunta a la orden
6. El archivo aparece como adjunto principal en la orden de venta

Instalación
-----------

1. Copiar el módulo a la carpeta de addons de Odoo
2. Actualizar la lista de módulos
3. Instalar el módulo "Web Pay Shipping Methods"
4. Configurar los proveedores de pago según sea necesario

Uso
---

1. Ir a la tienda web
2. Agregar productos al carrito
3. Proceder al checkout
4. En la página de pago, seleccionar transferencia bancaria
5. Subir el comprobante de transferencia (opcional)
6. Completar el pedido

Configuración Técnica
--------------------

El módulo incluye:

* **Modelos extendidos**: `payment.provider` y `sale.order`
* **Controladores personalizados**: Manejo de archivos y validación
* **Templates QWeb**: Interfaz de usuario para subida de archivos
* **JavaScript**: Validación del lado del cliente y envío de archivos

Archivos Principales
-------------------

* `models/payment_provider.py`: Extensión del modelo de proveedores de pago
* `models/sale_order.py`: Extensión del modelo de órdenes de venta
* `controllers/main.py`: Controladores para manejo de archivos
* `views/payment_transfer_receipt_templates.xml`: Templates de la interfaz

Compatibilidad
--------------

* Odoo 18.0
* Módulos requeridos: website_sale, payment

Licencia
--------

GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3)

Autor
-----

Cybrosys Technologies Pvt. Ltd.
