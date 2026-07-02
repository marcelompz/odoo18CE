# AEX Delivery Carrier for Odoo

## Overview

Este módulo integra los servicios de envío nacionales **AEX** (Paraguay) con las aplicaciones de comercio electrónico e inventario de Odoo. Permite gestionar todo el proceso de envío directamente desde Odoo, desde la obtención de tarifas de envío en tiempo real en el proceso de compra hasta la generación de etiquetas de envío y el seguimiento de paquetes.

Este conector es compatible con **Odoo versión 18.0**.

## Main Features

- **Cálculo de tarifas en tiempo real**: Calcula automáticamente los costos de envío de AEX en el carrito de compras del comercio electrónico según el peso, las dimensiones y el destino del paquete.
- **Generación de envíos**: Crea envíos en el sistema AEX directamente a partir de órdenes de entrega validadas de Odoo.
- **Impresión de etiquetas**: Obtiene y adjunta la etiqueta de envío oficial de AEX (PDF) a la orden de entrega en Odoo.
- **Cancelación de envíos**: Permite cancelar un envío generado desde la interfaz de Odoo. - **Seguimiento de paquetes**: Proporciona un enlace directo a la página de seguimiento de AEX para cada envío.
- **Mapeo automático de ciudades**: Asigna inteligentemente la ciudad del cliente (campo de texto) a los códigos oficiales de ciudad de AEX, simplificando el proceso de compra.
- **Gestión de ciudades**: Incluye una herramienta para importar y mantener actualizada la lista de ciudades compatibles con AEX directamente desde su API.

## Installation

1. Copie la carpeta `delivery_aex` en el directorio `addons` de Odoo.
2. Reinicie el servidor de Odoo.
3. Vaya a **Aplicaciones** en su instancia de Odoo.
4. Haga clic en **Actualizar lista de aplicaciones**.
5. Busque "Integración de entrega de AEX" y haga clic en **Instalar**.

## Configuration

### 1. Configurar las credenciales de AEX

Antes de usar el conector, debe ingresar sus credenciales de la API de AEX.

1. Vaya a **Inventario → Configuración → Métodos de envío**.
2. Busque y abra el método de envío de **AEX**.
3. En la pestaña **Configuración de AEX**, verá los siguientes campos:

- **Entorno**: Cambie entre los entornos de prueba (Sandbox) y producción.
- **Clave pública de AEX**: Ingrese su clave pública de AEX.
- **Clave privada de AEX**: Ingrese su clave privada de AEX.

5. Haga clic en **Guardar**.

### 2. Importar ciudades de AEX

El conector necesita una lista de ciudades oficiales de AEX para calcular las tarifas correctamente.

1. Vaya a **Contactos → Configuración → AEX → Importar Ciudades AEX**.
2. Se abrirá un asistente. Haga clic en el botón **Importar/Actualizar Ciudades**.
3. El sistema se conectará a la API de AEX y completará los datos necesarios de la ciudad. Recibirá una notificación al finalizar.
   _Debe ejecutar este proceso periódicamente para mantener la lista de ciudades actualizada._

### 3. Configurar la Dirección de la Empresa

Asegúrese de que la dirección del almacén de su empresa tenga asignada una ciudad AEX correspondiente.

1. Vaya a **Contactos** y busque el registro de contactos de su empresa.
2. En los detalles de la dirección, asegúrese de que el campo "País" sea Paraguay y que el campo "Ciudad" esté correctamente completado.
3. El sistema intentará buscar la ciudad automáticamente. Para mayor seguridad, puede seleccionar manualmente la ciudad correcta en el menú desplegable **Ciudad AEX**.

### 4. Habilitar en el sitio web

Finalmente, habilite el método de envío AEX para su tienda de comercio electrónico.

1. Vaya a **Sitio web → Configuración → Ajustes**.
2. En la sección **Envío**, asegúrese de que la opción "Envío" esté activada.
3. Añada **AEX** a la lista de métodos de envío disponibles.

## Usage

### En comercio electrónico

- Los clientes que compren en su sitio web verán AEX como opción de envío durante el proceso de compra.
- El coste del envío se calculará automáticamente en función de los artículos del carrito y la dirección de envío.
- El sistema intentará encontrar automáticamente la ciudad introducida por el cliente. Si no se encuentra una ciudad válida, no se mostrará la opción de envío AEX.

### En el backend (procesamiento de pedidos)

1. Al confirmar un pedido de venta con envío AEX, se crea una **Orden de entrega**.
2. Abra la orden de entrega desde el módulo **Inventario**.
3. Tras validar la transferencia, aparecerá el botón inteligente "Seguimiento".
4. El envío AEX se crea automáticamente y el número de seguimiento se completa en el campo "Referencia de seguimiento del transportista".
5. La etiqueta de envío oficial de AEX (PDF) se adjuntará al chatter de la orden de entrega. Puede imprimirla desde allí.

## Contribution

Si encuentra algún problema o tiene alguna sugerencia para mejorar este módulo, no dude en abrir un problema o enviar una solicitud de extracción en GitHub.

## Authors

Crossnexion EAS

Brindamos soluciones integrales a las empresas de forma continua, utilizando las herramientas tecnológicas como aliado estratégico.

- [LinkedIn](https://www.linkedin.com/company/crossnexion/)
- [GitHub](https://github.com/crossnexion)
- [crossnexion.com](https://crossnexion.com)
- [Facebook](https://www.facebook.com/crossnexion/)
- [Instagram](https://www.instagram.com/crossnexion/)
