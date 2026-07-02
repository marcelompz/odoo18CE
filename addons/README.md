# Custom Odoo Modules – Proyecto UTEX

Repositorio de módulos personalizados desarrollados para Odoo 18 por Crossnexion EAS.

---

## 📦 Módulo utex_stock_cross

## 📝 Historial de mejoras

- 2025-12-15 | Se agrega campo color al producto, m2o relacionado al modelo product.attribute.value
- 2025-12-15 | Se cambia visibilidad de los campos ancho y gramatura solo cuando clase de producto == mercadería
- 2025-12-18 | Se agregan campo Código (char) en los modelos product.model y product.initial, con esos campos se concatenan para generar el codigo del producto
- 2025-12-18 | Se agrega campo Modelo del producto (m2o) relacionado al modelo product.model en la plantilla de cotización
- 2026-02-09 | Se agrega validación de fechas antes de guardar.
- 2026-03-09 | Se agregan iconos de acceso directo a nuevo producto y nuevo embalaje.
- 2026-04-07 | Se agrega el campo código en Combinacion de Telas y se actualiza lógica de nombre en Productos.
- 2026-04-08 | Se agrega grupo de usuario para forzar la no creación de productos.
- 2026-04-20 | Se agrega gestión de permisos para Unidades de Medida.

---

## 📦 Módulo supplier_invoice_cross

## 📝 Historial de mejoras

- 2026-01-07 | Se agrega modulo de acceso mas directo a las facturas proveedores, con control de timbrado con sus vencimientos.
- 2026-01-09 | Se ajusta para que al seleccionar el proveedor ya estire el ultimo timbrado cargado.
- 2026-03-06 | Se agrega la opcion de marcar cuando es timbrado de factura electronica.

---

## 📦 Módulo internal_purchase_requisition_cross

## 📝 Historial de mejoras

- 2025-12-16 | solo se puede elegir productos que estan marcados para la compra, además se quita el campo de precio al cargar el producto en la requisicion de compra
- 2025-12-16 | se quita el domain del modulo principal para que muestre todos los contactos al crear la compra
- 2025-12-16 | sumatoria de cantidades cuando se repiten productos en la requisicion de compra
- 2025-12-16 | ajuste en la impresion de la requisicion de compra
- 2025-12-16 | se agrega icono en el menú principal para crear una requisición de compra de forma más directa
- 2025-12-16 | se agrega campo que concatena lista de productos para mostrar en la vista de lista
- 2025-12-16 | al crear una nueva requisición ya trae, si tiene asignado, el departamento del usuario
- 2025-12-16 | se agrega opcion de cargar varios productos a la vez
- 2025-12-16 | se agrega boton para acortar pasos de aprobaciones
- 2025-12-16 | se agrega campo de prioridad
- 2025-12-16 | se mejora las busquedas y agrupaciones
- 2025-12-16 | se agrega una lista de productos en los departamentos de los empleados, para que en la requisicion se pueda filtrar por esos productos
- 2025-12-16 | se agregan campos de configuraciones en productos para calculos de cantidades en la compra
- 2025-12-16 | numero de ficha en la solicitud de requisicion de compra
- 2025-12-16 | modificacion de vista de lista al seleccionar varios productos para cargar en la solicitud
- 2025-12-16 | campo relacionado con la compra, y cambio a estado comprado
- 2025-12-16 | campos de largo, ancho y gramatura en el albarán
- 2025-12-16 | se crean reglas para que el usuario vea sus propios documentos y gerencia vea de todos
- 2025-12-16 | cambio de string del campo requested_by
- 2025-12-16 | se agrega campo de cliente con filtro de contactos relacionados con el campo requested_by
- 2025-12-17 | Se agrega campo Precio x Mts en los detalles del proveedor en el producto para luego llevar en el producto
- 2025-12-18 | Se aplica obligatoriedad a campos del proveedor en productos cuando apply_weight_product == True
- 2026-01-12 | Se agrega las opciones de embalajes en requisicion de compra.
- 2026-01-12 | Se agrega el campo linear_meter (float) en el modelo product.packaging para ser visualizado en la requisicion de compra.
- 2026-01-13 | Se agrega campo calculado del total de metro lineal en la requisicion de compra.
- 2026-01-13 | Mejora en la creación de órdenes de compra agrupando por proveedor y producto; se añade campo de proveedor en la vista de requisiciones.
- 2026-01-23 | Se agrega la opcion de modificar el proveedor, igual si ya fue confirmado y se de agregar motivo de cancelacion.
- 2026-01-28 | Se añade campos de rechazo en la línea de requisición de compra.
- 2026-02-03 | Se agrega campos adicionales en la línea de la orden de compra y crear vista para el producto.
- 2026-02-05 | Se ajusta impresion de solicitud de presupuesto de compra.
- 2026-02-09 | Se implementa lógica para compras rápidas y estándar, y se actualizan estados de requisición.
- 2026-02-10 | Se ajusta campos de orden de compra en la línea de requisición de compra.
- 2026-02-19 | Se agrega en la vista de selección de productos para departamento un botón para poder editar los productos.
- 2026-04-20 | Se dehabilita el acceso a los datos de la unidad de medida desde el formulario de requisicion de compras.

---

## 📦 Módulo internal_purchase_requisition

## 📝 Historial de mejoras

- 2026-01-28 | Se corrige llamado de vista tree a list.

---

## 📦 Módulo utex_account_cros

## 📝 Historial de mejoras

- 2026-02-03 | Se agrega campos nro operacion, banco y titular a los pagos de clientes/proveedores.
- 2026-02-06 | Se ajusta para que muestre el campo de importe con impuestos en la linea de facturas.
- 2026-02-25 | Se agrega reporte de estado de cuentas de cliente.
- 2026-03-06 | Se habilita la creación de nuevos tipos de documentos.
- 2026-04-20 | Se validar fecha de factura antes de enviar documento electrónico.
- 2026-06-06 | Se ajusta validación de fecha en factura para cumplimiento de reglas de envío.
- 2026-06-10 | Se introdujo un nuevo grupo de seguridad para permitir la eliminación de facturas en cualquier estado.

---

## 📦 Módulo utex_purchase_cros

## 📝 Historial de mejoras

- 2026-02-06 | Se agrega modulo que muestra el campo de importe con impuestos en la linea de compra.
- 2026-03-06 | Se agregra campo para mostrar números de factura en órdenes de compra.

---

## 📦 Módulo ms_stock_report

## 📝 Historial de mejoras

- 2026-02-23 | Se agregan las columnas de precios de ventas unitario y total, y magen en el reporte de stock actual.

---

## 📦 Módulo inventory_turnover_report_analysis

## 📝 Historial de mejoras

- 2026-03-03 | Se agrega campo para filtrar solo compras y ventas en el informe de rotación.

---

## 📦 Módulo advanced_receiptmoney_cross

## 📝 Historial de mejoras

- 2026-03-03 | Se agrega un borde a la pagina del recibo de dinero.

---

## 📦 Módulo utex_sale_cross

## 📝 Historial de mejoras

- 2026-03-04 | Se agrega informe de lista de materiales necesarios para la compra.
- 2026-03-04 | Se agrega números de factura en la vista lista de órdenes de venta.
- 2026-03-06 | Se agrega campos de cantidad entregada y facturada en el modelo de pedido de venta, tambien se ocultan campos solicitados de la vista de lista.

---

## 📦 Módulo pos_payment_reference_cross

## 📝 Historial de mejoras

- 2026-03-10 | Se agrega el campo referencia de pago en la vista de lista de pos.order.

---

## 📦 Módulo sale_order_prepayment_cross

## 📝 Historial de mejoras

- 2026-03-10 | Se cambia la vista wizard para registrar el anticipo.
- 2026-04-23 | Se ajusta la vista de cotizaciones para que muestre ya el botón de `Registrar anticipo` al guardar un borrador.

---

## 📦 Módulo sale_detalles_cross

## 📝 Historial de mejoras

- 2026-04-06 | Se agrega lógica para sincronizar el código de barras desde el default_code en el modelo product.product

---

## 📦 Módulo reporte_compraventa

## 📝 Historial de mejoras

- 2026-04-23 | Se ajusta el codigo para que trabaje mejor en multiempresa.
- 2026-06-03 | Se agrega procesamiento de notas de crédito en el reporte de libro ventas.
- 2026-06-09 | Se modificar criterios de búsqueda en reportes de compras y ventas para incluir facturas con número de factura.

---

## ⚠️ Notas importantes

---
