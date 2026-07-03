# POS Customer Balance & Settle Due (Community Edition)

Este módulo es una extensión para Odoo 19 Community Edition que permite a los cajeros visualizar el saldo pendiente de los clientes y registrar el cobro de estas deudas directamente desde el Punto de Venta (TPV).

## Arquitectura y Justificación Técnica

### El problema en Odoo Community (CE)
Odoo Enterprise Edition (EE) incluye de forma nativa la funcionalidad de "Settle Due", la cual permite cobrar dinero a la cuenta de un cliente sin venderle ningún producto. A nivel técnico, Odoo EE logra esto saltándose el flujo normal de `pos.order` y generando directamente un `account.payment` que luego inyecta en la caja de la sesión (`pos.session`) mediante excepciones especiales en su código fuente privativo.

Replicar este comportamiento exacto en la versión Community Edition es altamente riesgoso porque el motor base del TPV en CE **exige que toda entrada de dinero esté respaldada por una orden de venta (`pos.order`) que contenga al menos una línea de producto**. Si se intenta forzar una orden vacía, el sistema falla al realizar el cierre de caja.

### Nuestra Solución: El "Hack Elegante" del Producto Fantasma
Para lograr exactamente el mismo flujo contable y de experiencia de usuario que la versión Enterprise sin desestabilizar el motor de Odoo CE, hemos implementado la solución del **"Producto Fantasma"**:

1. **Producto Oculto Automático**: El sistema crea automáticamente un producto de tipo servicio llamado `Abono de Cuenta`. Este producto está protegido contra borrado o modificación por capas de seguridad en Python.
2. **Registro de Cobro Transparente**: Cuando el cajero presiona el botón "Pagar Saldo", el sistema añade silenciosamente este producto a la orden por el valor exacto de la deuda. Esto satisface la necesidad del TPV de tener una orden válida, permitiendo que el dinero ingrese a caja perfectamente.
3. **Limpieza en Reportes de Ventas**: Para evitar que este producto infle los ingresos comerciales en los análisis, hemos sobreescrito la vista SQL de los reportes del TPV (`report.pos.order`) para excluir permanentemente cualquier registro asociado a este producto fantasma. Así, los reportes de ventas se mantienen prístinos y reales.
4. **Reconciliación Contable Perfecta (Emulación EE)**: Mediante código en el backend (`pos_order.py`), interceptamos la creación de estas órdenes especiales. Anulamos la entrada financiera a la cuenta de "Ingresos por Ventas" y generamos un asiento compensatorio que envía el dinero directamente a **"Cuentas por Cobrar"** del cliente. El código luego concilia automáticamente este crédito contra las facturas pendientes, cancelando la deuda real en la contabilidad.

### Conclusión
Esta arquitectura permite que el usuario administre cobranzas desde el TPV con total fluidez, manteniendo una contabilidad estricta y reportes limpios, pero respetando las reglas de validación del core de Odoo Community Edition.
