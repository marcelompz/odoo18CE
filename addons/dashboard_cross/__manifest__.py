# -*- coding: utf-8 -*-
{
    'name': 'Dashboards Crossnexion',
    'version': '18.0.1.42.2',
    'category': 'Extra Tools',
    'summary': 'Dashboards interactivos basados en TailwindCSS',
    'description': """
        Client Actions con dashboards Owl/Tailwind para Odoo 18.

        Novedades 1.42.2 (03.06.2026 - Fix totales + ancho tablas):
          * Fix: la fila TOTAL de las tablas (Ventas por dias / por mes) salia
            en texto oscuro sobre fondo navy (ilegible) por un conflicto de
            especificidad CSS; ahora se ve en blanco.
          * Las tablas usan tipografia/espaciado mas compactos y el contenido
            de Ventas por dias / por mes usa el ancho completo, para que los
            12 meses entren sin scroll horizontal en pantallas anchas.

        Novedades 1.42.1 (03.06.2026 - Rango 12 meses por defecto):
          * Todos los tableros con filtro de fecha arrancan con un rango de
            12 meses (inicio a fin, terminando en el mes actual):
              - Reporte Gerencial y Ventas por dias: date_from/date_to = 12m.
              - Productos y Compras: preset por defecto '12m' (antes '6m').
              - Ventas por mes: ya estaba en '12m'.

        Novedades 1.42.0 (03.06.2026 - Leyenda de rango en todos los tableros):
          * La leyenda de rango de fechas (gris claro, DD/MM/YYYY) bajo cada
            grafico y el check para ocultarla/mostrarla se extienden a
            Ventas por dias, Ventas por mes, Productos y Compras (antes solo
            estaba en Reporte Gerencial).
          * El check vive en el filtro de cada tablero (panel hover o sidebar)
            y no recarga datos.

        Novedades 1.41.0 (03.06.2026 - Leyenda de rango bajo los graficos):
          * Reporte Gerencial: debajo de cada grafico se muestra, en gris
            claro, el rango de fechas activo (DD/MM/YYYY → DD/MM/YYYY).
          * Nuevo check en los filtros ("Mostrar el rango de fecha debajo de
            cada grafico") para ocultar/mostrar esa leyenda. Activado por
            defecto; el toggle no recarga datos.

        Novedades 1.40.1 (03.06.2026 - Fix tendencia Reporte Gerencial):
          * La "Tendencia de Ventas" ahora muestra exactamente los meses del
            rango filtrado. Antes, si el rango era menor a 6 meses, se
            rellenaba hacia atrás hasta 6 (mostraba meses fuera del filtro).

        Novedades 1.40.0 (03.06.2026 - Filtros: colapsable + rango de fechas):
          * Reporte Gerencial: la barra de filtros (fechas, producto,
            categoria, cliente) ahora es la misma franja colapsable
            "⌄ FILTROS" que el resto; se despliega al pasar el mouse y el
            contenido aprovecha todo el alto.
          * Ventas por dias: nuevo filtro por RANGO de fechas (Desde/Hasta).
            Los chips de mes pasan a multi-seleccion y ARMAN el rango
            (ej. May+Jun -> 1-may a 30-jun); tambien se puede ajustar las
            fechas a mano (resalta los meses correspondientes).
          * Si el rango abarca mas de un mes, la tabla principal agrupa por
            MES (una columna por mes) en vez de por dia.
          * Comparativo y Proyeccion ahora trabajan sobre el rango elegido:
            comparativo = periodo actual vs mismo periodo del anio anterior;
            proyeccion = lineal sobre el rango + periodo anterior equivalente.
          * Backend get_sales_by_manager_data acepta date_from/date_to y
            decide agrupacion dia/mes; mantiene compatibilidad year/month.

        Novedades 1.39.0 (03.06.2026 - Identidad Perfipar en todos los tableros):
          * Reporte Gerencial, Productos y Compras adoptan la identidad
            corporativa Perfipar: encabezado con logo de la compania +
            titulo centrado y regla navy, paleta azul marino y acentos
            dorados, igual que VENTAS PERFIPAR / RESUMEN MENSUAL.
          * Implementado con una clase liviana ".o_pf_theme" que define las
            variables y repinta la paleta Odoo (morado/teal/naranja) a navy/
            azul/dorado sin alterar el layout propio de cada tablero.
          * Paletas de graficos (STACK_COLORS y colores sueltos) migradas de
            #017E84 / #714B67 / #E97B58 a navy / celeste / dorado.
          * Backend: get_commercial_data, get_product_dashboard_data y
            get_purchase_dashboard_data ahora devuelven company (logo+nombre)
            para el encabezado.

        Novedades 1.38.0 (03.06.2026 - Rediseno corporativo Perfipar):
          * "Ventas por dias" (VENTAS PERFIPAR) y "Ventas por mes"
            (RESUMEN MENSUAL) rediseniados para replicar los reportes
            corporativos Perfipar: paleta azul marino, encabezado con
            logo de la compania (servido desde res.company) + titulo
            centrado y regla navy, acento dorado para dolares y badges
            verdes para variacion positiva.
          * Tablas con encabezado navy de texto blanco, fila TOTAL navy,
            columna DOLARES con header dorado.
          * "Ventas por dias": tabla diaria + 4 paneles (Comparativo
            trimestre mini-tabla con badge %, grafico comparativo,
            tabla Proyeccion [Gs / USD / mes anterior + ratio], donut
            de Participacion) + Informe de Ventas + barra inferior navy.
          * "Ventas por mes": linea de evolucion + tarjeta TOTAL PERIODO,
            tabla mensual por gerencia y 4 KPIs (promedio, mejor, menor,
            periodo) con iconos circulares.
          * Backend: get_sales_by_manager_data devuelve company (logo+nombre)
            y, para la tabla de Proyeccion, total del mes anterior por
            gerencia (USD) + ratio proyeccion/mes-anterior.
            get_monthly_summary_data tambien devuelve company.
          * Las etiquetas de dia vuelven a formato "dia-mes" (2-may) para
            coincidir con el reporte de referencia.
          * Estilos nuevos en CSS propio (tailwind.min.css purgado).

        Novedades 1.37.0 (03.06.2026 - Mejoras visuales Ventas por dias / mes):
          * Barra de filtros (año/mes y presets) ahora se oculta y solo se
            revela al pasar el mouse por una franja delgada superior
            ("⌄ FILTROS"). Libera espacio vertical para el contenido.
          * "Ventas Diarias por Gerencia": los encabezados de día muestran
            solo el número (01, 02, ...) en un chip circular morado, sin el
            mes (ya referenciado arriba). Encabezado con degradado y borde
            morado; columnas TOTAL (azul) y USD (ámbar) resaltadas.
          * "Detalle Mensual por Gerencia": meses en chips morados y en
            español (ene-25, feb-25, ...) en vez de abreviaturas en inglés.
          * Comparativo Trimestre: etiquetas "Q2" reemplazadas por término
            latinoamericano "T2" (Trimestre 2).
          * Nota técnica: los estilos nuevos se agregaron como CSS propio en
            dashboard_cross.css porque el tailwind.min.css empaquetado está
            purgado y no incluye utilidades de color/gradiente adicionales.

        Novedades 1.36.0 (03.06.2026 - Reordenamiento de menus):
          * Estructura de menus reordenada:
              Dashboards Cross
              └── Comercial
                  ├── Compras
                  └── Ventas
                       ├── Reporte Gerencial
                       ├── Productos
                       ├── Ventas por dias
                       └── Ventas por mes
          * "Compras" pasa a colgar directo de Comercial (antes del submenu
            Ventas).
          * "Productos" se movio dentro del submenu Ventas.
          * Renombres:
              - "Comercial" -> "Reporte Gerencial"
              - "Resumen de Venta 1" / "Ventas por Gerencia" -> "Ventas por dias"
              - "Resumen de Venta 2" / "Resumen Mensual" -> "Ventas por mes"
          * Nombres de las acciones (breadcrumb) actualizados para coincidir
            con las nuevas etiquetas del menu.

        Novedades 1.35.0 (Reorganizacion de menus + filtros horizontales):
          * Menus reorganizados en 3 niveles para limpiar el top bar:
              Dashboards Cross
              └── Comercial
                  ├── Ventas (Comercial, Resumen de Venta 1, Resumen de Venta 2)
                  ├── Productos
                  └── Compras
          * Ventas por Gerencia renombrada a "Resumen de Venta 1".
          * Resumen Mensual renombrado a "Resumen de Venta 2".
          * Filtros movidos del sidebar lateral a una barra horizontal arriba
            (sticky) en los dashboards "Resumen de Venta 1" y "Resumen de
            Venta 2". Quedan accesibles sin tomar espacio horizontal del
            contenido principal.

        Novedades 1.34.0 (Tableros estilo Perfipar):
          * Dos nuevos dashboards bajo Dashboards Cross:
            - "Ventas por Gerencia": vista diaria del mes seleccionado con
              detalle por vendedor (invoice_user_id), comparativo trimestre
              actual vs mismo trimestre del anio anterior, proyeccion lineal
              del mes, participacion (donut), informe de ventas apilado.
              Equivalente USD calculado con conversion estandar de Odoo.
            - "Resumen Mensual": evolucion del total mensual (linea) +
              tabla mensual por vendedor + KPIs (promedio, mejor mes,
              peor mes, periodo analizado).
          * Filtros: ano + mes (Ventas por Gerencia), preset 3/6/9/12
            (Resumen Mensual).
          * Drills: click en vendedor abre sus facturas; click en mes
            abre todas las facturas del mes; click en segmento del donut
            abre las facturas del vendedor.
          * Mismo grupo de acceso (dashboard_cross.group_dashboard_cross_user).

        Novedades 1.33.0 (Fase 4: Dashboard de Compras):
          * Nuevo menu "Compras" bajo Dashboards Cross (mismo grupo de acceso
            que los otros dashboards).
          * KPIs: Total Invertido (IVA incl., neto de notas de credito),
            Facturas de Compra, Proveedores activos, Productos distintos.
          * Tendencia mensual: barras de compras del periodo + linea
            superpuesta de ventas para comparar (toggle opcional). Total
            mensual de compras encima de cada barra. Tooltip muestra ratio
            Ventas/Compras del mes.
          * Top 10 Proveedores: barras horizontales por monto neto comprado.
          * Compras por Categoria: donut con %, leyenda compacta clickeable.
          * Top 10 Productos Comprados: barras horizontales + tabla
            colapsable.
          * Backend: nuevo endpoint get_purchase_dashboard_data sobre
            account.move (in_invoice/in_refund posteadas).

        Novedades 1.32.0 (Fase 3: Clasificacion ABC / Pareto):
          * Ranking de Productos ahora clasifica cada SKU en clase A, B o C
            segun facturacion acumulada:
              - A: hasta 80% acumulado (productos top)
              - B: 80% a 95% acumulado (medio)
              - C: 95% a 100% acumulado (cola larga)
          * Resumen de Pareto en el header del Ranking: muestra # SKUs y %
            de facturacion por clase, con cuadrito de color.
          * Nueva columna "ABC" en la tabla del Ranking con badge circular
            de color (verde A / amber B / slate C). Tooltip muestra el
            acumulado exacto del producto.
          * Tooltip del chart de Ranking ahora incluye la clase ABC y el
            acumulado.

        Novedades 1.31.0 (Fase 2: Insights automaticos):
          * Nuevo panel "Insights del periodo" arriba del chart mensual.
            Compara el periodo actual contra el periodo anterior de misma
            duracion y emite hasta 8 insights ordenados por relevancia:
              - Facturacion total subio/cayo X%
              - Margen promedio subio/cayo X pp
              - Categorias con cambio >= 30% (subida o caida)
              - Concentracion Pareto (top 20% productos = X% facturacion)
              - Alerta de stock muerto (% del capital sin movimiento)
              - Productos "resucitados" (vendieron despues de >1 anio sin ventas)
            Color por tipo: verde (positivo), rojo (negativo), amber (alerta),
            indigo (info). Click en insight de categoria abre las lineas del rubro.
          * Backend: nuevo endpoint get_dashboard_insights que reusa los datos
            ya cargados y agrega una sola consulta del periodo anterior.

        Novedades 1.30.0 (Uniformizacion fase 1):
          * Reorden de secciones del Dashboard de Productos:
              1. KPIs
              2. Ventas Mensuales por Producto/Categoria (+ semanal on-demand)
              3. Resumen por Categoria (donut + leyenda + tabla)
              4. Ranking de Productos (chart + tabla)
              5. Origen del Stock Vendido (KPIs + donut + tabla)
              6. Stock Muerto / Inmovilizado (KPIs + donut + bars + tabla)
            La narrativa va de lo general a lo especifico y termina con
            los charts de "problema" agrupados al final.
          * Tamanos de chart estandarizados: donuts 256x256 px, bars 320 px.
          * Tipografia de descripciones uniformada a text-xs text-slate-500
            (antes mezclaba text-[10px] / text-[11px] con slate-400).

        Novedades 1.29.0:
          * Stock Muerto / Top 10: nuevos chips "Días sin venta" arriba del
            chart (Todos / >90d / >180d / >1a / >2a). Filtran los SKUs antes
            del Top 10 y reordenan por capital inmovilizado. El filtro
            tambien aplica en modo "Por Categoría" (agrega solo los SKUs
            que cumplen el criterio). Los productos nunca vendidos se
            incluyen en todos los rangos.
          * El titulo del chart muestra el rango activo (ej. "Top 10 SKUs
            por capital inmovilizado · > 1 a sin venta").

        Novedades 1.28.2:
          * Fix: legend de los charts stacked usaba `index` en vez de
            `datasetIndex`, lo que causaba el crash
            "Cannot read properties of null (reading '_resolveAnimations')"
            al hacer click en la leyenda mientras se navegaba a otro menu.
            Se agrego ademas un onClick defensivo que silencia el error
            si el chart ya fue destruido.

        Novedades 1.28.1:
          * Stock Muerto: donut achicado a 224x224 px y centrado verticalmente
            respecto a los KPIs de la izquierda para mejor proporcion visual.

        Novedades 1.28.0:
          * Charts mensual y semanal: leyenda derecha ahora muestra
            "Nombre (XX.X%)" por cada categoría/producto, calculado sobre
            el total del período. La línea del año anterior conserva su
            estilo de raya cortada.
          * Cuando "Mostrar % en gráficos" está activo, ahora también se
            pinta el porcentaje dentro de cada segmento apilado del chart
            mensual/semanal (sólo si el segmento es ≥8% del total de su
            barra, para no saturar).

        Novedades 1.27.0:
          * Stock Muerto: nuevo donut al costado de los 4 KPIs que muestra la
            distribucion del capital inmovilizado entre las 3 clasificaciones
            (Sin movimiento / Baja rotacion / Saludable). Centro del donut
            con capital total y # SKUs. Tooltip incluye monto, %, # SKUs y
            antiguedad promedio por clasificacion.

        Novedades 1.26.0:
          * Stock Muerto: toggle "Por Producto / Por Categoria" en el chart
            de capital inmovilizado. En modo Categoria agrupa los SKUs por
            su categoria, ordena por capital total descendente, y colorea
            con la paleta categorial (consistente con el Resumen por
            Categoria). Tooltip muestra: capital, # SKUs, unidades,
            antiguedad promedio y mix de clasificaciones (Sin mov./Baja
            rot./Saludable). Click en la barra abre las lineas de la
            categoria.

        Novedades 1.25.0:
          * Checkbox global "Mostrar % en gráficos" en el sidebar. Cuando esta
            activo (default), los donuts pintan el porcentaje dentro de cada
            segmento (>3%). Tooltips y leyendas siempre muestran %.
          * Resumen por Categoria: leyenda compacta ahora muestra cuadrito de
            color (12px con borde y sombra), monto y % discreto al lado.
            Funciona en los tres modos (Venta / Cantidad / Margen).
          * KPI cards de Origen del Stock Vendido y de Stock Muerto: cuadritos
            de referencia mas grandes (12px) y con borde sutil para destacar.

        Novedades 1.24.0:
          * Resumen por Categoria: toggle Venta / Cantidad / Margen en el
            donut. La leyenda compacta tambien refleja la metrica activa.
          * Stock Muerto / Inmovilizado: ahora muestra un grafico de barras
            con el Top 10 SKUs por capital inmovilizado, coloreado segun
            clasificacion (rojo / amber / verde). La tabla detallada queda
            como "Ver detalle" colapsable, con los filtros (checkboxes y
            chips de dias sin vender) movidos al interior del detalle.

        Novedades 1.23.0:
          * Resumen por Categoria: ahora muestra un donut con la distribucion
            de facturacion + leyenda compacta clickeable. La tabla queda como
            "Ver detalle" colapsable. Click en un segmento del donut o en la
            leyenda abre las lineas de la categoria.
          * Ranking de Productos: nuevo grafico de barras horizontales con el
            Top 10 segun el orden activo (Monto / Cantidad / Antiguedad /
            Margen). La tabla detallada queda como "Ver detalle" colapsable.
            Click en una barra abre las lineas de factura del producto.

        Novedades 1.22.1:
          * Fix: el boton "Ocultar detalle" del Origen del Stock Vendido ahora
            cierra correctamente (antes siempre abria). Se elimino el scroll
            automatico al expandir para que el donut/KPI con el que se
            interactuo siga visible justo arriba del detalle.

        Novedades 1.22.0:
          * "Origen del Stock Vendido": vista principal mas limpia. La tabla
            detallada se oculta por default y aparece como seccion expandible
            al hacer click en un KPI card o segmento del donut. Los 3
            checkboxes se mueven al detalle (contextuales). Boton "Ver todo
            el detalle / Ocultar detalle" en el header. Scroll automatico al
            detalle al abrirlo.

        Novedades 1.21.0:
          * Nueva seccion "Stock Muerto / Inmovilizado" en Dashboard de Productos.
            Identifica SKUs con stock disponible y rotacion pobre, calificandolos en:
              - SIN MOVIMIENTO: stock > 0 y sin ventas en el periodo activo.
              - BAJA ROTACION: vendio pero la cobertura excede 6 meses.
              - SALUDABLE: cobertura aceptable.
            Cada KPI muestra capital inmovilizado, # SKUs y antiguedad promedio.
            Tabla con stock, valor, ultima venta, dias sin vender, cobertura
            (meses) y antiguedad. Filtros locales por clasificacion + chips
            "Mas de N dias sin vender" (0/90/180/365/730).
          * Backend: nuevo endpoint get_stock_dead_inventory que combina
            stock.quant (stock fisico), account.move (ultima venta y ventas
            del periodo) y stock.move (primera recepcion).

        Novedades 1.20.0:
          * "Origen del Stock Vendido": cada KPI card muestra la antigüedad
            promedio (en días o anios) de los productos de esa clasificación.
            El tooltip del donut también incluye promedio simple y
            promedio ponderado por cantidad vendida.

        Novedades 1.19.0:
          * Nueva seccion "Origen del Stock Vendido" en el Dashboard de
            Productos. Clasifica cada producto vendido en el periodo en:
              - NUEVO (verde): primera compra dentro del periodo activo.
              - REPOSICION (amber): historial previo + compra dentro del periodo.
              - STOCK ANTIGUO (slate): vendido sin reposicion reciente.
            Visualizacion: 3 KPI cards con %/facturacion + donut + tabla
            filtrable por checkbox (Nuevo / Reposicion / Stock Antiguo).
          * Cada fila incluye: fecha de 1ra compra y fecha de reposicion en el
            periodo (cuando corresponde), facturacion, cantidad y margen %.

        Novedades 1.18.0:
          * Acceso restringido por usuario: nuevo grupo "Usuario Dashboard"
            bajo la categoria "Dashboards Cross". Solo los usuarios marcados
            ven los menus Comercial y Productos y pueden invocar el endpoint.
            Por default se asigna al admin; el resto se habilita desde el
            formulario del usuario en Configuracion > Usuarios.

        Novedades 1.17.0:
          * Top N configurable en el chart (8 / 15 / 25). Util cuando el
            catalogo es disperso y el segmento "Otros" domina la barra.
          * Indicador de coverage: subtitulo del chart muestra que % de la
            facturacion del periodo cubre el Top N.
          * Tooltip del chart en modo 'index': al pasar el mouse por una
            barra aparecen todos los segmentos del mes en un solo tooltip,
            con el Total mes correctamente calculado.
          * Comparativo vs anio anterior: el tooltip ahora muestra delta y %
            cuando esta activo el preset 12m comparativo.
          * Click en "Otros" abre las lineas de factura solamente de los
            items que NO estan en el Top (filtra por product_id NOT IN top).

        Novedades 1.16.0:
          * Dashboard de Productos: se eliminaron los filtros "Categoria" y
            "Productos" del sidebar (toggle Producto/Categoria y el resumen de
            categorias hacen el mismo trabajo). El sidebar queda con Periodo
            + Antiguedad, mas limpio.
          * Se quito la carga inicial de product.category y product.product
            (search_read con limit 500), acelerando el primer render.

        Novedades 1.15.0:
          * Dashboard de Productos: nueva seccion "Resumen por Categoria"
            (entre el chart mensual y el ranking). Muestra cada categoria con
            su color (paleta del chart en modo Categoria), # de productos,
            cantidad, facturacion, margen y margen %, ordenado por facturacion
            desc y margen desc. Click en una fila abre las lineas de factura
            del rubro filtradas por el periodo activo.

        Novedades 1.14.0:
          * Ranking de productos: nuevo boton "Por Margen" y dos columnas nuevas
            "Margen" (valor) y "Margen %" (badge de color: rojo si <=0, amber
            si 0-15%, verde si >=15%). Calculo: revenue - standard_price * qty.

        Novedades 1.13.0:
          * Dashboard de Productos: el sidebar reemplaza los inputs Desde/Hasta
            por chips de preset (3m, 6m, 9m, 12m) + boton "12m vs anio anterior".
          * Preset "12m vs anio anterior": agrega una linea punteada al chart
            mensual con el total mes a mes del mismo periodo del anio pasado,
            sin romper la lectura del stack actual.
          * Backend: nuevo parametro `preset` en get_product_dashboard_data que
            resuelve fechas automaticamente; cuando preset='12m_compare' devuelve
            tambien `previous_year.total_per_month`.

        Novedades 1.12.0:
          * Dashboard de Productos: toggle "Por Producto / Por Categoria" en el
            chart mensual y semanal. En modo Categoria las barras agrupan los
            Top 8 rubros + Otros y la antiguedad se oculta del tooltip (no
            aplica a la categoria como un todo).
          * Ranking de productos con tres modos de orden: Por Monto, Por
            Cantidad, Por Antiguedad (default cuando se activa modo Categoria).
            El ranking siempre lista productos individuales, no categorias.
          * Icono de ayuda (i) en el header del chart con tooltip explicativo.
          * Drill por segmento de categoria: abre las lineas de factura del
            rubro respetando el periodo y filtros activos.

        Novedades 1.11.0:
          * Se removio la seccion "Top 10 Productos (Ultimos 3 meses)" del
            Dashboard Comercial: ahora vive exclusivamente en el Dashboard de
            Productos (con desglose mensual + semanal + ranking con antiguedad).
          * Backend: se elimino el computo de top_products_3m en get_commercial_data
            para reducir carga (la version equivalente esta en get_product_dashboard_data).

        Novedades 1.10.0:
          * Vista tree de drill (lineas de factura) ahora incluye una columna
            "Antig. (dias)" antes del campo Estado, calculada a partir de la
            primera recepcion del producto (fallback create_date).
          * Default order de la vista tree: fecha descendente (ventas mas
            nuevas primero).
          * Checkbox "Ver por semana" en el dashboard de Productos para no
            chocar con el click de drill. Manejo robusto de Chart.js para
            evitar errores "getParsed" en destruccion/recreacion de charts.

        Novedades 1.9.0:
          * Dashboard de Productos: desglose SEMANAL on-demand. Debajo del grafico
            mensual hay chips por mes; al hacer click se abre un segundo grafico
            apilado con las 4 semanas del mes (dias 1-7, 8-14, 15-21, 22-fin),
            usando los mismos Top 8 productos + Otros. Cada semana muestra su
            total y los segmentos son clickeables (drill a lineas de factura).
          * Total de la suma mensual y semanal pintado encima de cada barra.

        Novedades 1.8.0:
          * Nuevo Dashboard de Productos (menu separado) con sidebar de filtros
            a la izquierda (fechas, categoria, productos multi-seleccion, rango
            de antiguedad).
          * Grafico de barras apiladas: ventas mensuales con desglose por Top 8
            productos + segmento "Otros". Antiguedad visible en el tooltip.
          * Ranking de productos con columna de antiguedad (badge de color) y
            toggle Monto / Cantidad.
          * Click en barra o fila abre la vista tree de lineas de factura del
            producto en el periodo activo.

        Novedades 1.7.1:
          * "En Negociacion" ahora incluye presupuestos (draft/sent) Y ventas
            confirmadas (sale/done) que aun no tienen factura asociada. El drill
            del KPI muestra el mismo conjunto.

        Novedades 1.7.0:
          * Nuevo widget: Top 10 Productos vendidos en los ultimos 3 meses con
            antiguedad (dias desde la primera recepcion en stock). Barras horizontales
            coloreadas por antiguedad (verde &lt;90d, ambar &lt;1a, slate &gt;1a) y badge
            de antiguedad sobre cada barra. Toggle Monto/Cantidad.
          * Click sobre una barra (o fila de la tabla) abre la vista tree de lineas
            de factura (account.move.line) del producto en ese periodo.

        Novedades 1.5.0:
          * Portafolio de productos: codigo separado del nombre, filas clickeables (abren ficha).
          * Top Vendedores y Top Clientes: filas clickeables a res.users / res.partner.
          * Montos con whitespace-nowrap (no se cortan a dos lineas).
          * Badges para porcentaje de margen y dias de rotacion.

        Novedades 1.4.0:
          * Tendencia de Ventas / Metodos de Pago / Composicion del Margen respetan
            el rango de fechas del filtro (antes eran 6 meses fijos).
          * Labels incluyen el anio (Abr/26) cuando el rango supera 12 meses o cruza anios.
          * Rango menor a 6 meses: se completan 6 buckets hacia atras para que la
            tendencia no quede casi vacia.

        Novedades 1.3.0:
          * Fuente de datos: FACTURAS (account.move posteadas). Notas de credito restan.
          * En Negociacion sigue sobre sale.order. Funnel/conversion sobre crm.lead.

        Novedades 1.2.0:
          * Montos con moneda local (simbolo/decimales/posicion).
          * IVA incluido en todos los totales.
          * Assets vendorizados locales.
          * days_in_stock calculado con ultima venta real.
          * Salud del Cliente respeta filtros.
    """,
    'author': 'Crossnexion',
    'website': 'https://www.crossnexion.com',
    'depends': ['base', 'web', 'sale_management', 'crm', 'account'],
    'data': [
        'security/dashboard_cross_security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_menu_views.xml',
        'views/res_config_settings_views.xml',
        'views/invoice_drill_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dashboard_cross/static/src/components/commercial_dashboard.js',
            'dashboard_cross/static/src/components/commercial_dashboard.xml',
            'dashboard_cross/static/src/components/product_dashboard.js',
            'dashboard_cross/static/src/components/product_dashboard.xml',
            'dashboard_cross/static/src/components/purchase_dashboard.js',
            'dashboard_cross/static/src/components/purchase_dashboard.xml',
            'dashboard_cross/static/src/components/sales_by_manager.js',
            'dashboard_cross/static/src/components/sales_by_manager.xml',
            'dashboard_cross/static/src/components/monthly_summary.js',
            'dashboard_cross/static/src/components/monthly_summary.xml',
            'dashboard_cross/static/src/css/dashboard_cross.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}
