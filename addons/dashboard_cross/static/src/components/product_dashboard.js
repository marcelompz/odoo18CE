/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

const LIB = {
    jquery:     "/dashboard_cross/static/src/lib/jquery-3.7.1.min.js",
    chart:      "/dashboard_cross/static/src/lib/chart.umd.min.js",
    select2Js:  "/dashboard_cross/static/src/lib/select2.min.js",
    select2Css: "/dashboard_cross/static/src/lib/select2.min.css",
    tailwind:   "/dashboard_cross/static/src/lib/tailwind.min.css",
};

// Paleta de 8 colores para el stack (consistente entre meses)
const STACK_COLORS = [
    '#1c3d6e', // odoo-teal
    '#c8992f', // odoo-orange
    '#7ba3cc', // odoo-purple
    '#3B82F6', // blue
    '#10B981', // emerald
    '#F59E0B', // amber
    '#6366F1', // indigo
    '#EC4899', // pink
];
const OTHERS_COLOR = '#CBD5E1'; // slate-300

export class ProductDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loading: true,
            viewMode: 'amount', // 'amount' | 'quantity' | 'antiquity' | 'margin' (ranking)
            groupMode: 'product', // 'product' | 'category' (apilado del chart)
            weekMode: false,    // checkbox: si esta activo, click en barra abre semanal
            showMobileFilters: false,
            showRangeCaption: true,
            filters: {
                preset: '12m', // '3m' | '6m' | '9m' | '12m' | '12m_compare'
                antiquity: 'all', // 'all' | 'lt90' | '90_365' | 'gt365'
                top_n: 8, // 8 | 15 | 25
                show_pct: true, // pintar % en los segmentos de donuts/bars
                // category_id y product_ids quedaron deprecados (sin UI). Se siguen
                // enviando al backend como falsy para no romper la firma del endpoint.
                category_id: "",
                product_ids: [],
                // Selector de compañía: [] = todas (suma todo). Si tiene ids, filtra.
                company_ids: [],
                // Check "Impuesto incluido" (IVA). false = neto (default).
                tax_included: false,
            },
            // Opciones del selector de compañía (llegan del backend).
            companies: [],
            // Filtros locales del bloque "Origen del Stock Vendido"
            // (no se envían al backend; recalculan la vista en memoria)
            originFilters: {
                new: true,
                replenished: true,
                old_stock: true,
            },
            // Detalle del bloque "Origen del Stock Vendido" (collapsible).
            // Vacío en la vista principal; click en KPI o donut lo abre.
            originDetail: {
                active: false,
                only: null, // si está seteado, la TABLA de detalle se filtra a esa sola
                            // clasificación (drill por click), sin tocar el donut.
            },
            // Detalle (collapsible) del Resumen por Categoría
            categoryDetail: { active: false },
            // Métrica del donut por categoría: 'revenue' | 'qty' | 'margin'
            categoryViewMode: 'revenue',
            // Detalle (collapsible) del Ranking de Productos
            rankingDetail: { active: false },
            // Detalle (collapsible) de Stock Muerto / Inmovilizado
            deadDetail: { active: false },
            // Modo del chart Top 10 de Stock Muerto: 'product' | 'category'
            deadChartMode: 'product',
            // Filtro "días sin venta" SOLO para el chart top 10
            // 0 = todos; 90/180/365/730 = >= ese nro de días (incluye "nunca vendidos")
            deadChartDaysFilter: 0,
            // Filtros locales del bloque "Stock Muerto / Inmovilizado"
            deadFilters: {
                no_movement: true,
                low_rotation: true,
                healthy: false,    // por default ocultamos los saludables (foco en problemas)
                min_days_no_sale: 0, // 0 = sin filtro, 90/180/365/730 segun chip
            },
            deadInventory: {
                loading: true,
                data: {
                    period: { date_from: '', date_to: '' },
                    summary: {
                        no_movement:  { count: 0, value: 0, qty_available: 0, avg_antiquity_days: 0 },
                        low_rotation: { count: 0, value: 0, qty_available: 0, avg_antiquity_days: 0 },
                        healthy:      { count: 0, value: 0, qty_available: 0, avg_antiquity_days: 0 },
                    },
                    totals: { total_value: 0, total_skus: 0, total_qty: 0 },
                    thresholds: { low_rotation_months: 6 },
                    items: [],
                },
            },
            // Insights automáticos (panel arriba)
            insights: {
                loading: false,
                items: [],
            },
            data: {
                currency: { symbol: '', name: '', position: 'before', decimal_places: 2 },
                period: { date_from: '', date_to: '', preset: '6m' },
                months: { labels: [], ranges: [], total_per_month: [] },
                monthly_stack: { datasets: [] },
                previous_year: null,
                ranking_by_revenue: [],
                ranking_by_qty: [],
                ranking_by_antiquity: [],
                ranking_by_margin: [],
                abc_summary: {
                    A: { count: 0, revenue: 0, product_pct: 0, revenue_pct: 0 },
                    B: { count: 0, revenue: 0, product_pct: 0, revenue_pct: 0 },
                    C: { count: 0, revenue: 0, product_pct: 0, revenue_pct: 0 },
                },
                category_summary: [],
                all_ranking: [],
                stock_origin_summary: {
                    period: { date_from: '', date_to: '' },
                    totals: { product_count: 0, revenue: 0 },
                    new: { count: 0, revenue: 0, qty: 0, margin: 0, revenue_pct: 0, margin_pct: 0, avg_antiquity_days: 0, avg_antiquity_days_weighted: 0 },
                    replenished: { count: 0, revenue: 0, qty: 0, margin: 0, revenue_pct: 0, margin_pct: 0, avg_antiquity_days: 0, avg_antiquity_days_weighted: 0 },
                    old_stock: { count: 0, revenue: 0, qty: 0, margin: 0, revenue_pct: 0, margin_pct: 0, avg_antiquity_days: 0, avg_antiquity_days_weighted: 0 },
                },
                totals: { product_count: 0, total_revenue: 0, total_qty: 0 },
            },
            weekly: {
                active: false,
                loading: false,
                month_idx: null,
                month_label: '',
                data: {
                    weeks: { labels: [], ranges: [], total_per_week: [] },
                    weekly_stack: { datasets: [] },
                    month: { start: '', end: '', label: '' },
                },
            },
        });

        onWillStart(async () => {
            try { await loadCSS(LIB.tailwind); } catch (e) { console.error("Tailwind CSS load", e); }
        });

        onMounted(async () => {
            try {
                if (!window.Chart) await loadJS(LIB.chart);
            } catch (e) { console.error("Core libs", e); }

            await this.fetchData();
            this.state.loading = false;
            setTimeout(() => this.renderCharts(), 100);
        });

        onWillUnmount(() => {
            // Destruir charts para evitar errores de eventos pendientes en Chart.js
            this._destroyChartByCanvasId('pdMonthlyStackCanvas');
            this._destroyChartByCanvasId('pdWeeklyStackCanvas');
            this._destroyChartByCanvasId('pdStockOriginCanvas');
            this._destroyChartByCanvasId('pdCategorySummaryCanvas');
            this._destroyChartByCanvasId('pdRankingCanvas');
            this._destroyChartByCanvasId('pdDeadInventoryCanvas');
            this._destroyChartByCanvasId('pdDeadDonutCanvas');
            window.pdMonthlyStackObj = null;
            window.pdWeeklyStackObj = null;
            window.pdStockOriginObj = null;
            window.pdCategorySummaryObj = null;
            window.pdRankingObj = null;
            window.pdDeadInventoryObj = null;
            window.pdDeadDonutObj = null;
        });
    }

    /** Destruye cualquier instancia de Chart asociada a un canvas (patron robusto). */
    _destroyChartByCanvasId(canvasId) {
        if (!window.Chart) return;
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const existing = window.Chart.getChart ? window.Chart.getChart(canvas) : null;
        if (existing) {
            try { existing.destroy(); } catch (e) { /* noop */ }
        }
    }

    // ============================================================
    // Bloque "Origen del Stock Vendido"
    // ============================================================

    /** Etiqueta legible para la clasificación. */
    originLabel(key) {
        return ({
            'new': 'Nuevo',
            'replenished': 'Reposición',
            'old_stock': 'Stock Antiguo',
        })[key] || key;
    }

    /**
     * Callback Chart.js para legend.labels.generateLabels en stacked bars.
     * Agrega el % del período al lado de cada nombre de la leyenda derecha.
     * Excluye datasets tipo 'line' (línea del año anterior) del cálculo del %,
     * pero los muestra al final con su color de borde.
     *
     * IMPORTANTE: usamos `datasetIndex` (no `index`) porque es el campo que
     * Chart.js usa internamente para identificar a qué dataset togglear
     * visibilidad al hacer click en la leyenda de un bar/line chart.
     */
    _stackedLegendWithPct() {
        return (chart) => {
            const datasets = chart.data.datasets || [];
            const barDatasets = datasets.filter(ds => ds.type !== 'line');
            const totals = barDatasets.map(ds => (ds.data || []).reduce((s, v) => s + (Number(v) || 0), 0));
            const grandTotal = totals.reduce((s, v) => s + v, 0);

            const items = barDatasets.map((ds) => {
                const origIdx = datasets.indexOf(ds);
                const t = totals[barDatasets.indexOf(ds)];
                const pct = grandTotal > 0 ? (t / grandTotal * 100).toFixed(1) : '0.0';
                return {
                    text: `${ds.label}  (${pct}%)`,
                    fillStyle: ds.backgroundColor,
                    strokeStyle: ds.backgroundColor,
                    lineWidth: 0,
                    hidden: !chart.isDatasetVisible(origIdx),
                    datasetIndex: origIdx,
                };
            });
            datasets.filter(ds => ds.type === 'line').forEach(ds => {
                const origIdx = datasets.indexOf(ds);
                items.push({
                    text: ds.label,
                    fillStyle: ds.borderColor || ds.backgroundColor,
                    strokeStyle: ds.borderColor || ds.backgroundColor,
                    lineWidth: 2,
                    lineDash: ds.borderDash || [],
                    hidden: !chart.isDatasetVisible(origIdx),
                    datasetIndex: origIdx,
                });
            });
            return items;
        };
    }

    /**
     * onClick defensivo para la leyenda de stacked charts. Evita el crash
     * "Cannot read properties of null (reading '_resolveAnimations')" cuando
     * el chart se destruye (por navegación) y todavía hay un evento de click
     * en vuelo. También cubre el caso de legendItem sin datasetIndex.
     */
    _stackedLegendOnClick(evt, legendItem, legend) {
        try {
            const chart = legend && legend.chart;
            if (!chart || !chart.config) return;
            const di = legendItem && legendItem.datasetIndex;
            if (di == null) return;
            if (chart.isDatasetVisible(di)) {
                chart.hide(di);
                legendItem.hidden = true;
            } else {
                chart.show(di);
                legendItem.hidden = false;
            }
        } catch (err) {
            // Silenciar: el chart probablemente se destruyó antes del click
            console.warn('Legend onClick suprimido (chart destruido):', err && err.message);
        }
    }

    /**
     * Plugin Chart.js que pinta % blanco dentro de cada segmento de una barra
     * apilada (stacked) cuando el segmento representa al menos `minPct`% del
     * total de esa barra. Excluye datasets tipo 'line'.
     */
    _stackedPctLabelsPlugin(enabled, minPct = 8) {
        if (!enabled) return [];
        return [{
            id: 'stackedPctLabels',
            afterDatasetsDraw: (chart) => {
                const { ctx } = chart;
                const datasets = chart.data.datasets || [];
                const barDatasets = datasets.filter(d => d.type !== 'line');
                const labels = chart.data.labels || [];
                ctx.save();
                ctx.font = 'bold 10px sans-serif';
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.shadowColor = 'rgba(0,0,0,0.35)';
                ctx.shadowBlur = 2;
                labels.forEach((_, xi) => {
                    const total = barDatasets.reduce(
                        (s, d) => s + Math.max(0, Number((d.data || [])[xi] || 0)), 0);
                    if (total <= 0) return;
                    barDatasets.forEach((ds) => {
                        const v = Number((ds.data || [])[xi] || 0);
                        if (v <= 0) return;
                        const pct = (v / total) * 100;
                        if (pct < minPct) return;
                        const origIdx = datasets.indexOf(ds);
                        const meta = chart.getDatasetMeta(origIdx);
                        const bar = meta?.data?.[xi];
                        if (!bar) return;
                        const yCenter = (bar.y + bar.base) / 2;
                        ctx.fillText(`${pct.toFixed(0)}%`, bar.x, yCenter);
                    });
                });
                ctx.restore();
            }
        }];
    }

    /**
     * Plugin Chart.js que dibuja porcentajes blancos dentro de los segmentos
     * de un donut. Si el segmento es menor a `minPct`, se omite (no entra).
     * Se devuelve un array (para spread en plugins[]) y se controla con un flag.
     */
    _pctLabelsPlugin(enabled, minPct = 3) {
        if (!enabled) return [];
        return [{
            id: 'donutPctLabels',
            afterDatasetsDraw: (chart) => {
                const { ctx } = chart;
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data) return;
                const ds = chart.data.datasets[0]?.data || [];
                const total = ds.reduce((s, v) => s + (Number(v) || 0), 0);
                if (total <= 0) return;
                ctx.save();
                ctx.font = 'bold 11px sans-serif';
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                meta.data.forEach((arc, i) => {
                    const v = Number(ds[i] || 0);
                    const pct = (v / total) * 100;
                    if (pct < minPct) return;
                    const angle = (arc.startAngle + arc.endAngle) / 2;
                    const r = (arc.innerRadius + arc.outerRadius) / 2;
                    const x = arc.x + Math.cos(angle) * r;
                    const y = arc.y + Math.sin(angle) * r;
                    // Sombra suave para legibilidad
                    ctx.shadowColor = 'rgba(0,0,0,0.35)';
                    ctx.shadowBlur = 2;
                    ctx.fillText(`${pct.toFixed(0)}%`, x, y);
                });
                ctx.restore();
            }
        }];
    }

    /** Color hex para badge de clasificación ABC. */
    abcColor(cls) {
        return ({ A: '#10B981', B: '#F59E0B', C: '#64748B' })[cls] || '#94A3B8';
    }

    /** Clases Tailwind para badge ABC (background tintado + texto). */
    abcBadgeClasses(cls) {
        return ({
            A: 'text-emerald-700 bg-emerald-50 border-emerald-200',
            B: 'text-amber-700 bg-amber-50 border-amber-200',
            C: 'text-slate-700 bg-slate-50 border-slate-200',
        })[cls] || 'text-slate-700 bg-slate-50 border-slate-200';
    }

    /** Formatea días como "Xd" si <365, sino "Y a" (años con 1 decimal). */
    formatAntiquityDays(days) {
        const d = Math.max(0, Math.round(Number(days) || 0));
        if (d < 365) return `${d} d`;
        return `${(d / 365).toFixed(1)} a`;
    }

    /** Color asociado a cada clasificación (consistente entre KPIs / donut / badges). */
    originColor(key) {
        return ({
            'new': '#10B981',         // emerald
            'replenished': '#F59E0B', // amber
            'old_stock': '#64748B',   // slate
        })[key] || '#94A3B8';
    }

    /** Toggle de los 3 checkboxes; redibuja el donut y la tabla filtrada. */
    toggleOriginFilter(key) {
        if (!(key in this.state.originFilters)) return;
        this.state.originFilters[key] = !this.state.originFilters[key];
        setTimeout(() => this.renderStockOriginChart(), 30);
    }

    /**
     * Abre la sección de detalle filtrada SOLO a la clasificación clickeada.
     * Si "all" es true, marca las 3 como activas (botón "Ver todo el detalle").
     * Si la clasificación clickeada ya era la única activa con el detalle abierto, cierra.
     */
    openOriginDetail(classification, all = false) {
        // El donut (originFilters) NO se toca: se controla con sus propios checkboxes
        // para poder comparar las 3 clasificaciones siempre. Acá solo abrimos la TABLA
        // de detalle, opcionalmente filtrada a una clasificación (drill por click).
        if (all || !classification) {
            this.state.originDetail.only = null; // mostrar todas en la tabla
        } else {
            // Si ya estaba filtrada a esta sola y abierta, se cierra (toggle).
            if (this.state.originDetail.active && this.state.originDetail.only === classification) {
                this.closeOriginDetail();
                return;
            }
            this.state.originDetail.only = classification;
        }
        this.state.originDetail.active = true;
    }

    /** Cierra la sección de detalle. */
    closeOriginDetail() {
        this.state.originDetail.active = false;
        this.state.originDetail.only = null;
    }

    /**
     * Toggle del botón "Ver todo el detalle / Ocultar detalle" del header.
     * Si está abierto cierra; si está cerrado abre con las 3 clasificaciones activas.
     */
    toggleOriginDetailFull() {
        if (this.state.originDetail.active) {
            this.closeOriginDetail();
        } else {
            this.openOriginDetail(null, true);
        }
    }

    // ============================================================
    // Resumen por Categoría — chart + detalle
    // ============================================================

    /** Toggle del detalle (tabla) del Resumen por Categoría. */
    toggleCategoryDetail() {
        this.state.categoryDetail.active = !this.state.categoryDetail.active;
    }

    /** Cambia la métrica del donut por categoría (revenue / qty / margin). */
    setCategoryViewMode(mode) {
        const valid = ['revenue', 'qty', 'margin'];
        if (!valid.includes(mode)) return;
        if (this.state.categoryViewMode === mode) return;
        this.state.categoryViewMode = mode;
        setTimeout(() => this.renderCategorySummaryChart(), 30);
    }

    /** Renderiza el donut del Resumen por Categoría según categoryViewMode. */
    renderCategorySummaryChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pdCategorySummaryCanvas');
        if (!canvas) return;
        const summary = this.state.data?.category_summary || [];
        if (!summary.length) {
            this._destroyChartByCanvasId('pdCategorySummaryCanvas');
            return;
        }
        const mode = this.state.categoryViewMode || 'revenue';
        const labels = summary.map(c => c.name);
        let data, metricLabel;
        if (mode === 'qty') {
            data = summary.map(c => c.qty || 0);
            metricLabel = 'Cantidad';
        } else if (mode === 'margin') {
            // En margen pueden aparecer negativos -> el donut no acepta valores negativos
            // visuales. Usamos abs() pero etiquetamos correctamente en el tooltip.
            data = summary.map(c => Math.max(0, c.margin || 0));
            metricLabel = 'Margen';
        } else {
            data = summary.map(c => c.revenue || 0);
            metricLabel = 'Facturación';
        }
        const colors = summary.map((_, i) => this.categoryColor(i));
        const total = data.reduce((s, x) => s + (x || 0), 0);
        const self = this;

        this._destroyChartByCanvasId('pdCategorySummaryCanvas');
        const showPct = this.state.filters.show_pct;
        window.pdCategorySummaryObj = new Chart(canvas, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }] },
            plugins: this._pctLabelsPlugin(showPct),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const cat = summary[elements[0].index];
                    if (cat && cat.category_id) {
                        self.drillCategoryLines(cat.category_id, cat.name);
                    }
                },
                onHover: (event, chartElements) => {
                    const target = event?.native?.target || event?.target;
                    if (target && target.style) {
                        target.style.cursor = (chartElements && chartElements.length) ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => {
                                const item = summary[c.dataIndex] || {};
                                let primary;
                                if (mode === 'qty') {
                                    const v = item.qty || 0;
                                    const pct = total > 0 ? (Math.abs(v) / total * 100).toFixed(1) : '0.0';
                                    primary = `${item.name}: ${v.toLocaleString()} u · ${pct}%`;
                                } else if (mode === 'margin') {
                                    const v = item.margin || 0;
                                    const pct = total > 0 ? (Math.max(0, v) / total * 100).toFixed(1) : '0.0';
                                    primary = `${item.name}: ${self.formatFullNumber(v)} · ${pct}%`;
                                } else {
                                    const v = item.revenue || 0;
                                    const pct = total > 0 ? (v / total * 100).toFixed(1) : '0.0';
                                    primary = `${item.name}: ${self.formatFullNumber(v)} · ${pct}%`;
                                }
                                return [
                                    primary,
                                    `Facturación: ${self.formatFullNumber(item.revenue || 0)}`,
                                    `Margen: ${self.formatFullNumber(item.margin || 0)} (${(item.margin_pct || 0).toFixed(1)}%)`,
                                    `Cantidad: ${(item.qty || 0).toLocaleString()} u`,
                                    'Click para ver líneas de la categoría',
                                ];
                            }
                        }
                    }
                }
            }
        });
    }

    // ============================================================
    // Ranking de Productos — chart + detalle
    // ============================================================

    /** Toggle del detalle (tabla) del Ranking de Productos. */
    toggleRankingDetail() {
        this.state.rankingDetail.active = !this.state.rankingDetail.active;
    }

    /** Lista activa según viewMode (la misma que usa la tabla del ranking). */
    get currentRankingList() {
        const m = this.state.viewMode;
        const d = this.state.data || {};
        if (m === 'margin') return d.ranking_by_margin || [];
        if (m === 'antiquity') return d.ranking_by_antiquity || [];
        if (m === 'quantity') return d.ranking_by_qty || [];
        return d.ranking_by_revenue || [];
    }

    /** Renderiza barras horizontales del Top 10 del Ranking según el viewMode. */
    renderRankingChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pdRankingCanvas');
        if (!canvas) return;
        const items = this.currentRankingList.slice(0, 10);
        if (!items.length) {
            this._destroyChartByCanvasId('pdRankingCanvas');
            return;
        }
        const mode = this.state.viewMode;
        const self = this;
        const formatYAxis = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
            return v;
        };

        const labels = items.map(p => {
            const code = p.code ? `[${p.code}] ` : '';
            const name = (p.name || '').length > 32 ? (p.name.slice(0, 30) + '…') : (p.name || '');
            return code + name;
        });
        let data, datasetLabel, axisFmt, barColor;
        if (mode === 'quantity') {
            data = items.map(p => p.qty || 0);
            datasetLabel = 'Cantidad';
            axisFmt = (v) => v;
            barColor = '#3B82F6'; // azul
        } else if (mode === 'antiquity') {
            data = items.map(p => p.antiquity_days || 0);
            datasetLabel = 'Antigüedad (días)';
            axisFmt = (v) => v;
            barColor = '#64748B'; // slate
        } else if (mode === 'margin') {
            data = items.map(p => p.margin || 0);
            datasetLabel = 'Margen';
            axisFmt = formatYAxis;
            barColor = '#6366F1'; // índigo
        } else {
            data = items.map(p => p.revenue || 0);
            datasetLabel = 'Facturación';
            axisFmt = formatYAxis;
            barColor = '#1c3d6e'; // odoo-teal
        }

        this._destroyChartByCanvasId('pdRankingCanvas');
        window.pdRankingObj = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: datasetLabel,
                    data,
                    backgroundColor: barColor,
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const item = items[elements[0].index];
                    if (item) self.drillProductLines(item.id, item.name);
                },
                onHover: (event, chartElements) => {
                    const target = event?.native?.target || event?.target;
                    if (target && target.style) {
                        target.style.cursor = (chartElements && chartElements.length) ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            title: (ctx) => {
                                const i = ctx[0].dataIndex;
                                return (items[i] || {}).name || '';
                            },
                            label: (c) => {
                                const item = items[c.dataIndex] || {};
                                const lines = [];
                                if (item.abc_class) {
                                    lines.push(`Clase ABC: ${item.abc_class} (acumulado ${(item.cum_pct || 0).toFixed(1)}%)`);
                                }
                                lines.push(`Facturación: ${self.formatFullNumber(item.revenue || 0)}`);
                                lines.push(`Cantidad: ${(item.qty || 0).toLocaleString()}`);
                                lines.push(`Margen: ${self.formatFullNumber(item.margin || 0)} (${(item.margin_pct || 0).toFixed(1)}%)`);
                                lines.push(`Antigüedad: ${self.formatAntiquityDays(item.antiquity_days || 0)}`);
                                lines.push('— Click para ver líneas de factura —');
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: '#f1f5f9' },
                        ticks: { callback: axisFmt, font: { size: 11 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { size: 11, weight: '500' } }
                    }
                }
            }
        });
    }

    /** Productos del período para la tabla de detalle.
     *  Si hay un drill activo (only) → solo esa clasificación.
     *  Si no → las clasificaciones marcadas en los checkboxes del donut. */
    get filteredOriginProducts() {
        const all = this.state.data?.all_ranking || [];
        const only = this.state.originDetail.only;
        if (only) return all.filter(p => (p.stock_origin || 'old_stock') === only);
        const f = this.state.originFilters || {};
        return all.filter(p => f[p.stock_origin || 'old_stock']);
    }

    /** Toggle del detalle (filtros + tabla) de Stock Muerto. */
    toggleDeadDetail() {
        this.state.deadDetail.active = !this.state.deadDetail.active;
    }

    /** Cambia el chart de Stock Muerto entre Top 10 SKUs vs Top 10 Categorías. */
    setDeadChartMode(mode) {
        if (mode !== 'product' && mode !== 'category') return;
        if (this.state.deadChartMode === mode) return;
        this.state.deadChartMode = mode;
        setTimeout(() => this.renderDeadInventoryChart(), 30);
    }

    /** Setea el filtro "días sin venta" para el chart top 10 (0=todos). */
    setDeadChartDaysFilter(n) {
        const v = parseInt(n) || 0;
        if (this.state.deadChartDaysFilter === v) return;
        this.state.deadChartDaysFilter = v;
        setTimeout(() => this.renderDeadInventoryChart(), 30);
    }

    /**
     * Items de stock muerto filtrados por "días sin venta" para el chart.
     * Si days_since_last_sale es null, se considera "nunca vendido" e ingresa
     * en todos los filtros mayores a 0 (porque es lo peor en rotación).
     */
    get filteredDeadItemsForChart() {
        const items = this.state.deadInventory.data?.items || [];
        const f = this.state.deadChartDaysFilter || 0;
        if (f <= 0) return items;
        return items.filter(it => {
            const d = it.days_since_last_sale;
            return d == null || d >= f;
        });
    }

    /**
     * Devuelve un color reutilizando la paleta categorial buscando por nombre
     * en el category_summary (los primeros 8 coinciden con el donut de Resumen).
     * Si la categoría no aparece en summary, se cae a OTHERS_COLOR (gris).
     */
    _catColorByName(name) {
        const idx = (this.state.data?.category_summary || []).findIndex(c => c.name === name);
        return this.categoryColor(idx);
    }

    /** Helper interno: agrupa una lista de items de stock muerto por categoría. */
    _aggregateDeadByCategory(items) {
        const byCat = {};
        for (const it of items) {
            const cid = it.category_id || 0;
            const key = `${cid}|${it.category || 'Sin Categoría'}`;
            if (!byCat[key]) {
                byCat[key] = {
                    category_id: cid,
                    name: it.category || 'Sin Categoría',
                    value: 0,
                    qty_available: 0,
                    sku_count: 0,
                    _ant_sum: 0,
                    cls_no_movement: 0,
                    cls_low_rotation: 0,
                    cls_healthy: 0,
                };
            }
            const b = byCat[key];
            b.value += it.value_in_stock || 0;
            b.qty_available += it.qty_available || 0;
            b.sku_count += 1;
            b._ant_sum += it.antiquity_days || 0;
            const c = it.classification || 'no_movement';
            if (c === 'no_movement') b.cls_no_movement += 1;
            else if (c === 'low_rotation') b.cls_low_rotation += 1;
            else b.cls_healthy += 1;
        }
        const list = Object.values(byCat).map(c => ({
            ...c,
            avg_antiquity_days: c.sku_count > 0 ? c._ant_sum / c.sku_count : 0,
        }));
        list.sort((a, b) => b.value - a.value);
        return list;
    }

    /** Aggregación por categoría usando TODOS los items (sin filtro). */
    get deadByCategoryAggregation() {
        return this._aggregateDeadByCategory(this.state.deadInventory.data?.items || []);
    }

    /**
     * Renderiza un donut con la distribución del capital inmovilizado entre
     * las 3 clasificaciones (Sin movimiento / Baja rotación / Saludable),
     * con el capital total y la cantidad de SKUs en el centro.
     */
    renderDeadDistributionChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pdDeadDonutCanvas');
        if (!canvas) return;

        const summary = this.state.deadInventory.data?.summary || {};
        const totals = this.state.deadInventory.data?.totals || {};
        const data = [
            summary.no_movement?.value || 0,
            summary.low_rotation?.value || 0,
            summary.healthy?.value || 0,
        ];
        const total = data.reduce((s, v) => s + v, 0);
        if (total <= 0) {
            this._destroyChartByCanvasId('pdDeadDonutCanvas');
            return;
        }
        const labels = ['Sin movimiento', 'Baja rotación', 'Saludable'];
        const colors = ['#EF4444', '#F59E0B', '#10B981'];
        const totalSkus = totals.total_skus || 0;
        const self = this;
        const showPct = this.state.filters.show_pct;

        this._destroyChartByCanvasId('pdDeadDonutCanvas');
        window.pdDeadDonutObj = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }]
            },
            plugins: [
                ...this._pctLabelsPlugin(showPct),
                {
                    id: 'deadCenterText',
                    beforeDraw: (chart) => {
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return;
                        const cx = (chartArea.left + chartArea.right) / 2;
                        const cy = (chartArea.top + chartArea.bottom) / 2;
                        ctx.save();
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.font = 'bold 10px sans-serif';
                        ctx.fillStyle = '#94a3b8';
                        ctx.fillText('CAPITAL TOTAL', cx, cy - 20);
                        ctx.font = 'bold 18px sans-serif';
                        ctx.fillStyle = '#1e293b';
                        ctx.fillText(self.formatCurrency(total), cx, cy + 2);
                        ctx.font = '11px sans-serif';
                        ctx.fillStyle = '#64748b';
                        ctx.fillText(`${totalSkus.toLocaleString()} SKUs`, cx, cy + 22);
                        ctx.restore();
                    }
                }
            ],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => {
                                const idx = c.dataIndex;
                                const key = ['no_movement', 'low_rotation', 'healthy'][idx];
                                const b = summary[key] || {};
                                const pct = total > 0 ? (c.raw / total * 100).toFixed(1) : '0.0';
                                return [
                                    `${labels[idx]}: ${self.formatFullNumber(c.raw)} · ${pct}%`,
                                    `${b.count || 0} SKUs · Antig. promedio: ${self.formatAntiquityDays(b.avg_antiquity_days || 0)}`,
                                ];
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Renderiza barras horizontales del Top 10 por capital inmovilizado:
     *  - mode='product': SKUs individuales, coloreados por clasificación.
     *  - mode='category': agrupado por categoría, colores categoriales.
     */
    renderDeadInventoryChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pdDeadInventoryCanvas');
        if (!canvas) return;

        const mode = this.state.deadChartMode || 'product';
        const self = this;
        const formatYAxis = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
            return v;
        };

        // Aplica filtro "días sin venta" antes de cortar Top 10
        const baseItems = this.filteredDeadItemsForChart;

        let items, labels, data, colors, datasetLabel;
        if (mode === 'category') {
            items = this._aggregateDeadByCategory(baseItems).slice(0, 10);
            if (!items.length) {
                this._destroyChartByCanvasId('pdDeadInventoryCanvas');
                return;
            }
            labels = items.map(c => c.name);
            data = items.map(c => c.value || 0);
            colors = items.map(c => self._catColorByName(c.name));
            datasetLabel = 'Capital inmovilizado por categoría';
        } else {
            items = baseItems.slice(0, 10);
            if (!items.length) {
                this._destroyChartByCanvasId('pdDeadInventoryCanvas');
                return;
            }
            labels = items.map(p => {
                const code = p.code ? `[${p.code}] ` : '';
                const name = (p.name || '').length > 32 ? (p.name.slice(0, 30) + '…') : (p.name || '');
                return code + name;
            });
            data = items.map(p => p.value_in_stock || 0);
            colors = items.map(p => self.deadColor(p.classification || 'no_movement'));
            datasetLabel = 'Capital inmovilizado por SKU';
        }

        this._destroyChartByCanvasId('pdDeadInventoryCanvas');
        window.pdDeadInventoryObj = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: datasetLabel,
                    data,
                    backgroundColor: colors,
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const item = items[elements[0].index];
                    if (!item) return;
                    if (mode === 'category') {
                        if (item.category_id) self.drillCategoryLines(item.category_id, item.name);
                    } else {
                        if (item.id) self.drillProductLines(item.id, item.name);
                    }
                },
                onHover: (event, chartElements) => {
                    const target = event?.native?.target || event?.target;
                    if (target && target.style) {
                        target.style.cursor = (chartElements && chartElements.length) ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            title: (ctx) => {
                                const i = ctx[0].dataIndex;
                                return (items[i] || {}).name || '';
                            },
                            label: (c) => {
                                const item = items[c.dataIndex] || {};
                                if (mode === 'category') {
                                    const lines = [
                                        `Capital: ${self.formatFullNumber(item.value || 0)}`,
                                        `${item.sku_count || 0} SKUs · ${(item.qty_available || 0).toLocaleString()} u`,
                                        `Antig. promedio: ${self.formatAntiquityDays(item.avg_antiquity_days || 0)}`,
                                    ];
                                    const m = item.cls_no_movement || 0;
                                    const l = item.cls_low_rotation || 0;
                                    const h = item.cls_healthy || 0;
                                    lines.push(`Sin mov.: ${m} · Baja rot.: ${l} · Saludable: ${h}`);
                                    lines.push('— Click para ver líneas de la categoría —');
                                    return lines;
                                }
                                const cls = self.deadLabel(item.classification || 'no_movement');
                                const lines = [
                                    `Estado: ${cls}`,
                                    `Stock: ${(item.qty_available || 0).toLocaleString()} u`,
                                    `Valor en stock: ${self.formatFullNumber(item.value_in_stock || 0)}`,
                                ];
                                if (item.days_since_last_sale != null) {
                                    lines.push(`Días sin vender: ${self.formatAntiquityDays(item.days_since_last_sale)}`);
                                } else {
                                    lines.push('Nunca se vendió');
                                }
                                if (item.months_of_stock != null) {
                                    lines.push(`Cobertura: ${item.months_of_stock.toFixed(1)} meses`);
                                }
                                lines.push('— Click para ver líneas de factura —');
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: '#f1f5f9' },
                        ticks: { callback: formatYAxis, font: { size: 11 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { size: 11, weight: '500' } }
                    }
                }
            }
        });
    }

    // ============================================================
    // Bloque "Stock Muerto / Inmovilizado"
    // ============================================================

    /** Etiqueta legible para la clasificación de stock muerto. */
    deadLabel(key) {
        return ({
            'no_movement':  'Sin movimiento',
            'low_rotation': 'Baja rotación',
            'healthy':      'Saludable',
        })[key] || key;
    }

    /** Color por clasificación de stock muerto. */
    deadColor(key) {
        return ({
            'no_movement':  '#EF4444',  // red-500
            'low_rotation': '#F59E0B',  // amber-500
            'healthy':      '#10B981',  // emerald-500
        })[key] || '#94A3B8';
    }

    /** Toggle de los 3 checkboxes de stock muerto. */
    toggleDeadFilter(key) {
        if (!(key in this.state.deadFilters)) return;
        this.state.deadFilters[key] = !this.state.deadFilters[key];
    }

    /** Setea el filtro "más de N días sin vender" (0 = sin filtro). */
    setDeadMinDays(n) {
        this.state.deadFilters.min_days_no_sale = parseInt(n) || 0;
    }

    /** Items del stock muerto filtrados (memoria). */
    get filteredDeadItems() {
        const items = this.state.deadInventory.data?.items || [];
        const f = this.state.deadFilters;
        const minDays = f.min_days_no_sale || 0;
        return items.filter(it => {
            if (!f[it.classification || 'no_movement']) return false;
            if (minDays > 0) {
                const d = it.days_since_last_sale;
                // "más de N días sin vender" incluye productos sin venta histórica
                if (d != null && d < minDays) return false;
            }
            return true;
        });
    }

    /** Renderiza el donut "Origen del Stock Vendido" respetando los filtros. */
    renderStockOriginChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pdStockOriginCanvas');
        if (!canvas) return;

        const summary = this.state.data?.stock_origin_summary || {};
        const f = this.state.originFilters || {};
        const order = ['new', 'replenished', 'old_stock'];
        const visible = order.filter(k => f[k]);
        const labels = visible.map(k => this.originLabel(k));
        const data = visible.map(k => (summary[k]?.revenue || 0));
        const colors = visible.map(k => this.originColor(k));
        const self = this;

        this._destroyChartByCanvasId('pdStockOriginCanvas');
        const showPct = this.state.filters.show_pct;
        window.pdStockOriginObj = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }],
            },
            plugins: this._pctLabelsPlugin(showPct),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const key = visible[elements[0].index];
                    if (key) self.openOriginDetail(key);
                },
                onHover: (event, chartElements) => {
                    const target = event?.native?.target || event?.target;
                    if (target && target.style) {
                        target.style.cursor = (chartElements && chartElements.length) ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => {
                                const key = visible[c.dataIndex];
                                const b = summary[key] || {};
                                const pct = (b.revenue_pct || 0).toFixed(1);
                                const avg = self.formatAntiquityDays(b.avg_antiquity_days || 0);
                                const wavg = self.formatAntiquityDays(b.avg_antiquity_days_weighted || 0);
                                return [
                                    `${self.originLabel(key)}: ${self.formatFullNumber(c.raw || 0)} · ${pct}%`,
                                    `Antig. promedio: ${avg} (ponderada por venta: ${wavg})`,
                                    'Click para ver el detalle',
                                ];
                            }
                        }
                    }
                },
            }
        });
    }

    /** Toggle del checkbox "Ver por semana". Al desactivar, se cierra el chart semanal. */
    toggleWeekMode() {
        this.state.weekMode = !this.state.weekMode;
        if (!this.state.weekMode) {
            this.closeWeekly();
        }
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
        this.renderCharts();
    }

    toggleMobileFilters() {
        this.state.showMobileFilters = !this.state.showMobileFilters;
    }

    /** Rango activo formateado (DD/MM/YYYY → DD/MM/YYYY) para la leyenda bajo los gráficos. */
    rangeLabel() {
        const fmt = (s) => {
            if (!s) return '';
            const p = String(s).split('-');
            return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : s;
        };
        const per = (this.state.data && this.state.data.period) || {};
        return `${fmt(per.date_from)} → ${fmt(per.date_to)}`;
    }

    setAntiquity(value) {
        this.state.filters.antiquity = value;
        this.applyFilters();
    }

    async applyFilters() {
        this.state.loading = true;
        await this.fetchData();
        this.state.loading = false;
        this.state.showMobileFilters = false;
        setTimeout(() => this.renderCharts(), 100);
    }

    async fetchData() {
        try {
            const payload = {
                preset: this.state.filters.preset || '6m',
                category_id: this.state.filters.category_id ? parseInt(this.state.filters.category_id) : false,
                product_ids: this.state.filters.product_ids || [],
                antiquity: this.state.filters.antiquity || 'all',
                group_by: this.state.groupMode || 'product',
                top_n: this.state.filters.top_n || 8,
                company_ids: this.state.filters.company_ids || [],
                tax_included: this.state.filters.tax_included || false,
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_product_dashboard_data",
                [payload]
            );
            if (resp) {
                this.state.data = resp;
                if (resp.companies) this.state.companies = resp.companies;
            }
        } catch (e) {
            console.error("ProductDashboard fetch error:", e);
        }
        // Stock muerto e insights en paralelo (no bloquean el render principal)
        this.fetchDeadInventory();
        this.fetchInsights();
    }

    /** Fetch independiente de insights automáticos. */
    async fetchInsights() {
        this.state.insights.loading = true;
        try {
            const payload = {
                preset: this.state.filters.preset || '6m',
                company_ids: this.state.filters.company_ids || [],
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_dashboard_insights",
                [payload]
            );
            if (resp && Array.isArray(resp.insights)) {
                this.state.insights.items = resp.insights;
            } else {
                this.state.insights.items = [];
            }
        } catch (e) {
            console.error("Insights fetch error:", e);
            this.state.insights.items = [];
        }
        this.state.insights.loading = false;
    }

    /** Click en un insight: si trae category_id, abre el drill de esa categoría. */
    onInsightClick(insight) {
        if (insight && insight.category_id) {
            this.drillCategoryLines(insight.category_id, insight.title || '');
        }
    }

    /** Fetch independiente de Stock Muerto / Inmovilizado. */
    async fetchDeadInventory() {
        this.state.deadInventory.loading = true;
        try {
            const payload = {
                preset: this.state.filters.preset || '6m',
                category_id: this.state.filters.category_id ? parseInt(this.state.filters.category_id) : false,
                company_ids: this.state.filters.company_ids || [],
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_stock_dead_inventory",
                [payload]
            );
            if (resp) this.state.deadInventory.data = resp;
        } catch (e) {
            console.error("Stock dead inventory fetch error:", e);
        }
        this.state.deadInventory.loading = false;
        // Renderizar charts de stock muerto cuando llegan los datos
        setTimeout(() => {
            this.renderDeadDistributionChart();
            this.renderDeadInventoryChart();
        }, 50);
    }

    /** Toggle "Mostrar % en gráficos". Re-renderiza todos los charts. */
    toggleShowPct() {
        this.state.filters.show_pct = !this.state.filters.show_pct;
        this.renderCharts();
    }

    /** Cambia cuantos items del Top mostrar (8, 15 o 25). */
    setTopN(n) {
        const valid = [8, 15, 25];
        if (!valid.includes(n)) return;
        if (this.state.filters.top_n === n) return;
        this.state.filters.top_n = n;
        this.applyFilters();
    }

    /** Cambia el preset de periodo (3m, 6m, 9m, 12m, 12m_compare). */
    setPreset(value) {
        const valid = ['3m', '6m', '9m', '12m', '12m_compare'];
        if (!valid.includes(value)) return;
        if (this.state.filters.preset === value) return;
        this.state.filters.preset = value;
        this.applyFilters();
    }

    /** Check "Impuesto incluido" (IVA): recalcula todo en la base elegida. */
    toggleTaxIncluded() {
        this.state.filters.tax_included = !this.state.filters.tax_included;
        this.applyFilters();
    }

    /** ¿Está marcada esta compañía? ([] = todas marcadas = suma todo). */
    isCompanySelected(companyId) {
        const sel = this.state.filters.company_ids || [];
        return sel.length === 0 || sel.includes(companyId);
    }

    /** Marca/desmarca una compañía. Si quedan todas (o ninguna), se normaliza a
     *  [] = todas (suma todo). Refresca todos los bloques. */
    toggleCompany(companyId) {
        const all = (this.state.companies || []).map(c => c.id);
        const current = new Set(
            (this.state.filters.company_ids && this.state.filters.company_ids.length)
                ? this.state.filters.company_ids
                : all
        );
        if (current.has(companyId)) current.delete(companyId);
        else current.add(companyId);
        // Si no queda ninguna, volvemos a "todas" (evita vista vacía).
        if (current.size === 0 || current.size === all.length) {
            this.state.filters.company_ids = [];
        } else {
            this.state.filters.company_ids = all.filter(id => current.has(id));
        }
        this.applyFilters();
    }

    /** Cambia entre apilar por producto / por categoria. */
    async setGroupMode(mode) {
        if (mode !== 'product' && mode !== 'category') return;
        if (this.state.groupMode === mode) return;
        this.state.groupMode = mode;
        // Al pasar a Categoria, default ranking a antiguedad. Al volver a Producto,
        // si estaba en antiguedad lo dejamos para no asumir; el usuario elige.
        if (mode === 'category' && this.state.viewMode === 'amount') {
            this.state.viewMode = 'antiquity';
        }
        // Re-fetch + re-render
        this.state.loading = true;
        await this.fetchData();
        // Si habia un weekly abierto, recargarlo con el nuevo group_by
        if (this.state.weekly.active && this.state.weekly.month_idx != null) {
            await this._refetchWeekly(this.state.weekly.month_idx);
        }
        this.state.loading = false;
        setTimeout(() => {
            this.renderCharts();
            if (this.state.weekly.active) this.renderWeeklyChart();
        }, 50);
    }

    /** Helper interno para re-fetchear el desglose semanal sin tocar UI. */
    async _refetchWeekly(idx) {
        const ranges = this.state.data?.months?.ranges || [];
        if (!ranges[idx]) return;
        const { start, end } = ranges[idx];
        try {
            const payload = {
                month_start: start,
                month_end: end,
                category_id: this.state.filters.category_id ? parseInt(this.state.filters.category_id) : false,
                product_ids: this.state.filters.product_ids || [],
                antiquity: this.state.filters.antiquity || 'all',
                group_by: this.state.groupMode || 'product',
                top_n: this.state.filters.top_n || 8,
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_product_weekly_breakdown",
                [payload]
            );
            if (resp) this.state.weekly.data = resp;
        } catch (e) {
            console.error("Weekly re-fetch error:", e);
        }
    }

    /** Drill por categoría (período actual del dashboard, respetando filtros). */
    drillCategoryLines(categoryId, name) {
        if (!categoryId) return;
        const f = this.state.filters;
        const period = this.state.data?.period || {};
        const domain = [
            ['parent_state', '=', 'posted'],
            ['display_type', '=', 'product'],
            ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
            ['product_id.categ_id', '=', categoryId],
        ];
        if (period.date_from) domain.push(['move_id.invoice_date', '>=', period.date_from]);
        if (period.date_to)   domain.push(['move_id.invoice_date', '<=', period.date_to]);
        if (f.product_ids && f.product_ids.length) {
            domain.push(['product_id', 'in', f.product_ids]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Líneas de Factura - Categoría: ${name || ''}`.trim(),
            res_model: 'account.move.line',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: {
                create: false,
                list_view_ref: 'dashboard_cross.view_dashboard_cross_move_line_drill_list',
            },
            target: 'current',
        });
    }

    /**
     * Drill: abre líneas de factura para un producto en el período actual,
     * respetando categoría si está seteada.
     */
    drillProductLines(productId, name) {
        if (!productId) return;
        const f = this.state.filters;
        const period = this.state.data?.period || {};
        const domain = [
            ['parent_state', '=', 'posted'],
            ['display_type', '=', 'product'],
            ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
            ['product_id', '=', productId],
        ];
        if (period.date_from) domain.push(['move_id.invoice_date', '>=', period.date_from]);
        if (period.date_to)   domain.push(['move_id.invoice_date', '<=', period.date_to]);
        if (f.category_id) domain.push(['product_id.categ_id', '=', parseInt(f.category_id)]);

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Líneas de Factura - ${name || ''}`.trim(),
            res_model: 'account.move.line',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: {
                create: false,
                list_view_ref: 'dashboard_cross.view_dashboard_cross_move_line_drill_list',
            },
            target: 'current',
        });
    }

    /**
     * Toggle del desglose semanal: si se hace click en el mismo mes, lo cierra;
     * si es otro mes, fetchea y muestra.
     */
    async selectMonth(idx) {
        const ranges = this.state.data?.months?.ranges || [];
        const labels = this.state.data?.months?.labels || [];
        if (!ranges[idx]) return;

        // Toggle: si ya estaba abierto en ese mes, lo cerramos
        if (this.state.weekly.active && this.state.weekly.month_idx === idx) {
            this.closeWeekly();
            return;
        }

        this.state.weekly.active = true;
        this.state.weekly.loading = true;
        this.state.weekly.month_idx = idx;
        this.state.weekly.month_label = labels[idx] || '';

        const { start, end } = ranges[idx];
        try {
            const payload = {
                month_start: start,
                month_end: end,
                category_id: this.state.filters.category_id ? parseInt(this.state.filters.category_id) : false,
                product_ids: this.state.filters.product_ids || [],
                antiquity: this.state.filters.antiquity || 'all',
                group_by: this.state.groupMode || 'product',
                top_n: this.state.filters.top_n || 8,
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_product_weekly_breakdown",
                [payload]
            );
            if (resp) this.state.weekly.data = resp;
        } catch (e) {
            console.error("Weekly breakdown error:", e);
        }
        this.state.weekly.loading = false;
        setTimeout(() => this.renderWeeklyChart(), 50);
    }

    closeWeekly() {
        this.state.weekly.active = false;
        this.state.weekly.month_idx = null;
        this.state.weekly.month_label = '';
        this._destroyChartByCanvasId('pdWeeklyStackCanvas');
        window.pdWeeklyStackObj = null;
    }

    /** Drill por semana + categoria. */
    _drillWeekCategory(weekIdx, categoryId, name) {
        const ranges = this.state.weekly.data?.weeks?.ranges || [];
        if (!ranges[weekIdx] || !categoryId) return;
        const { start, end } = ranges[weekIdx];
        const f = this.state.filters;
        const domain = [
            ['parent_state', '=', 'posted'],
            ['display_type', '=', 'product'],
            ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
            ['move_id.invoice_date', '>=', start],
            ['move_id.invoice_date', '<=', end],
            ['product_id.categ_id', '=', categoryId],
        ];
        if (f.product_ids && f.product_ids.length) {
            domain.push(['product_id', 'in', f.product_ids]);
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Líneas - Cat. ${name || ''} - ${this.state.weekly.month_label} ${this.state.weekly.data?.weeks?.labels?.[weekIdx] || ''}`.trim(),
            res_model: 'account.move.line',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: {
                create: false,
                list_view_ref: 'dashboard_cross.view_dashboard_cross_move_line_drill_list',
            },
            target: 'current',
        });
    }

    /** Drill por semana (filtra por rango de fecha de esa semana). Si onlyOthers, excluye top. */
    drillWeek(weekIdx, productId = null, productName = null, onlyOthers = false) {
        const ranges = this.state.weekly.data?.weeks?.ranges || [];
        if (!ranges[weekIdx]) return;
        const { start, end } = ranges[weekIdx];
        const f = this.state.filters;
        const ws = this.state.weekly.data?.weekly_stack || {};
        const domain = [
            ['parent_state', '=', 'posted'],
            ['display_type', '=', 'product'],
            ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
            ['move_id.invoice_date', '>=', start],
            ['move_id.invoice_date', '<=', end],
        ];
        if (productId) domain.push(['product_id', '=', productId]);
        if (f.category_id) domain.push(['product_id.categ_id', '=', parseInt(f.category_id)]);
        if (!productId && f.product_ids && f.product_ids.length) {
            domain.push(['product_id', 'in', f.product_ids]);
        }
        if (onlyOthers && !productId) {
            if ((ws.group_by === 'category') && Array.isArray(ws.top_category_ids) && ws.top_category_ids.length) {
                domain.push(['product_id.categ_id', 'not in', ws.top_category_ids]);
            } else if (Array.isArray(ws.top_product_ids) && ws.top_product_ids.length) {
                domain.push(['product_id', 'not in', ws.top_product_ids]);
            }
        }

        const wkLabel = this.state.weekly.data?.weeks?.labels?.[weekIdx] || '';
        const otherSuffix = onlyOthers ? ' - "Otros"' : '';
        const title = productId
            ? `Líneas - ${productName || ''} - ${this.state.weekly.month_label} ${wkLabel}`.trim()
            : `Líneas${otherSuffix} ${this.state.weekly.month_label} ${wkLabel}`.trim();

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: title,
            res_model: 'account.move.line',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: {
                create: false,
                list_view_ref: 'dashboard_cross.view_dashboard_cross_move_line_drill_list',
            },
            target: 'current',
        });
    }

    /**
     * Drill por mes. Si `onlyOthers` es true, excluye los IDs del Top N
     * (productos o categorias segun groupMode), asi el segmento "Otros"
     * abre solamente los items que estan en el segmento gris.
     */
    drillMonth(idx, onlyOthers = false) {
        const ranges = this.state.data?.months?.ranges || [];
        if (!ranges[idx]) return;
        const { start, end } = ranges[idx];
        const f = this.state.filters;
        const ms = this.state.data?.monthly_stack || {};
        const labels = this.state.data?.months?.labels || [];

        const domain = [
            ['parent_state', '=', 'posted'],
            ['display_type', '=', 'product'],
            ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
            ['move_id.invoice_date', '>=', start],
            ['move_id.invoice_date', '<=', end],
        ];
        if (f.category_id) domain.push(['product_id.categ_id', '=', parseInt(f.category_id)]);
        if (f.product_ids && f.product_ids.length) domain.push(['product_id', 'in', f.product_ids]);

        if (onlyOthers) {
            if ((ms.group_by === 'category') && Array.isArray(ms.top_category_ids) && ms.top_category_ids.length) {
                domain.push(['product_id.categ_id', 'not in', ms.top_category_ids]);
            } else if (Array.isArray(ms.top_product_ids) && ms.top_product_ids.length) {
                domain.push(['product_id', 'not in', ms.top_product_ids]);
            }
        }

        const title = onlyOthers
            ? `Líneas - "Otros" del mes ${labels[idx] || ''}`
            : `Líneas del mes ${labels[idx] || ''}`;

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: title,
            res_model: 'account.move.line',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: {
                create: false,
                list_view_ref: 'dashboard_cross.view_dashboard_cross_move_line_drill_list',
            },
            target: 'current',
        });
    }

    renderCharts() {
        if (!window.Chart) return;
        const formatYAxis = (value) => {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
        };
        const self = this;

        // Charts secundarios (resumen por categoría, ranking, origen del stock, stock muerto)
        this.renderStockOriginChart();
        this.renderCategorySummaryChart();
        this.renderRankingChart();
        // Stock muerto: solo si ya tenemos data (puede no haberse cargado aún)
        if (this.state.deadInventory.data?.items) {
            this.renderDeadDistributionChart();
            this.renderDeadInventoryChart();
        }

        // ===== 1) Stacked bar mensual (top 8 + Otros) =====
        const stackCanvas = document.getElementById('pdMonthlyStackCanvas');
        if (stackCanvas) {
            const months = this.state.data?.months || { labels: [] };
            const ds = (this.state.data?.monthly_stack?.datasets || []);
            const isCategoryMode = (this.state.data?.monthly_stack?.group_by === 'category');

            const chartDatasets = ds.map((d, i) => {
                const isOthers = (d._kind === 'category' ? d.category_id === 0 : d.product_id === 0);
                const color = isOthers ? OTHERS_COLOR : STACK_COLORS[i % STACK_COLORS.length];
                return {
                    label: (d.code ? `[${d.code}] ` : '') + (d.name || ''),
                    data: d.data || [],
                    backgroundColor: color,
                    borderColor: color,
                    borderWidth: 0,
                    stack: 'sales',
                    _kind: d._kind || 'product',
                    _antiquity_days: d.antiquity_days,
                    _antiquity_source: d.antiquity_source,
                    _product_id: d.product_id,
                    _category_id: d.category_id || 0,
                    _name: d.name,
                };
            });

            // Pre-calcular total por mes (suma SOLO de los datasets de barras apiladas)
            const monthTotals = (months.labels || []).map((_, i) =>
                chartDatasets.reduce((acc, d) => acc + (Number(d.data[i]) || 0), 0)
            );
            // (chartDatasets aun NO incluye el dataset linea del año anterior; se agrega después)

            // Si hay previous_year (preset 12m_compare), agregar dataset linea
            const py = this.state.data?.previous_year;
            if (py && Array.isArray(py.total_per_month) && py.total_per_month.length === (months.labels || []).length) {
                chartDatasets.push({
                    type: 'line',
                    label: 'Año anterior',
                    data: py.total_per_month,
                    borderColor: '#7ba3cc',          // odoo-purple
                    backgroundColor: 'rgba(113, 75, 103, 0.08)',
                    borderDash: [6, 4],
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#7ba3cc',
                    pointBorderWidth: 2,
                    pointHoverRadius: 6,
                    tension: 0.25,
                    fill: false,
                    stack: 'py',
                    order: 0, // se dibuja por encima
                    _kind: 'previous_year',
                });
            }

            // Patron robusto: destruir cualquier chart previo sobre el mismo canvas
            this._destroyChartByCanvasId('pdMonthlyStackCanvas');
            window.pdMonthlyStackObj = new Chart(stackCanvas, {
                type: 'bar',
                data: { labels: months.labels || [], datasets: chartDatasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: { padding: { top: 24 } }, // espacio para el label total
                    onClick: (evt, elements) => {
                        if (!elements || !elements.length) return;
                        const el = elements[0];
                        const idx = el.index;
                        // Si esta activo "Ver por semana", abrir desglose semanal sin drill
                        if (self.state.weekMode) {
                            self.selectMonth(idx);
                            return;
                        }
                        // Modo normal: drill segun tipo de segmento
                        const dsObj = chartDatasets[el.datasetIndex];
                        if (!dsObj) { self.drillMonth(idx); return; }
                        if (dsObj._kind === 'previous_year') return; // la linea no abre drill
                        if (dsObj._kind === 'category' && dsObj._category_id) {
                            self.drillCategoryLines(dsObj._category_id, dsObj._name);
                        } else if (dsObj._product_id) {
                            self.drillProductLines(dsObj._product_id, dsObj._name);
                        } else {
                            // Segmento "Otros": drill solo a los items que NO estan en el Top
                            self.drillMonth(idx, true);
                        }
                    },
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            position: 'right',
                            onClick: this._stackedLegendOnClick,
                            labels: {
                                boxWidth: 12,
                                font: { size: 11 },
                                generateLabels: this._stackedLegendWithPct(),
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: '#1e293b',
                            padding: 12,
                            displayColors: true,
                            filter: (item) => (item.raw || 0) !== 0, // ocultar segmentos en cero
                            callbacks: {
                                label: (c) => {
                                    const dsObj = chartDatasets[c.datasetIndex];
                                    const val = c.raw || 0;
                                    let line = `${dsObj.label}: ${self.formatFullNumber(val)}`;
                                    // En modo Categoria ocultamos antiguedad (no aplica a la categoria como un todo)
                                    if (!isCategoryMode && dsObj._antiquity_days != null && dsObj._kind !== 'previous_year') {
                                        const yrs = (dsObj._antiquity_days / 365).toFixed(1);
                                        const src = dsObj._antiquity_source === 'reception'
                                            ? '1ra recepción' : 'alta';
                                        line += ` · Antig. ${dsObj._antiquity_days}d (${yrs}a, ${src})`;
                                    }
                                    return line;
                                },
                                footer: (items) => {
                                    if (!items || !items.length) return '';
                                    // Sumar solo barras apiladas (excluir la linea del anio anterior)
                                    let sum = 0;
                                    let pyVal = null;
                                    items.forEach((it) => {
                                        const dsObj = chartDatasets[it.datasetIndex];
                                        if (!dsObj) return;
                                        if (dsObj._kind === 'previous_year') {
                                            pyVal = it.raw || 0;
                                        } else {
                                            sum += (it.raw || 0);
                                        }
                                    });
                                    const lines = [`Total mes: ${self.formatFullNumber(sum)}`];
                                    if (pyVal != null) {
                                        const delta = sum - pyVal;
                                        const pct = pyVal > 0 ? (delta / pyVal * 100) : 0;
                                        const arrow = delta >= 0 ? '▲' : '▼';
                                        lines.push(`vs Año anterior: ${self.formatFullNumber(pyVal)} (${arrow} ${pct.toFixed(1)}%)`);
                                    }
                                    return lines;
                                }
                            }
                        }
                    },
                    scales: {
                        x: { stacked: true, grid: { display: false } },
                        y: { stacked: true, ticks: { callback: formatYAxis }, grid: { color: '#f1f5f9' } }
                    }
                },
                plugins: [
                    {
                        id: 'monthlyTotalLabels',
                        afterDatasetsDraw: (chart) => {
                            const { ctx, scales } = chart;
                            const xScale = scales.x;
                            const yScale = scales.y;
                            if (!xScale || !yScale) return;
                            ctx.save();
                            ctx.font = 'bold 12px sans-serif';
                            ctx.fillStyle = '#1e293b';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            monthTotals.forEach((total, i) => {
                                if (!total) return;
                                const x = xScale.getPixelForValue(i);
                                const y = yScale.getPixelForValue(total);
                                ctx.fillText(self.formatCurrency(total), x, y - 6);
                            });
                            ctx.restore();
                        }
                    },
                    ...this._stackedPctLabelsPlugin(this.state.filters.show_pct),
                ]
            });
        }
    }

    /** Renderiza el chart semanal con la misma estética del mensual. */
    renderWeeklyChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pdWeeklyStackCanvas');
        if (!canvas) return;

        const weeks = this.state.weekly.data?.weeks || { labels: [] };
        const ds = (this.state.weekly.data?.weekly_stack?.datasets || []);
        const self = this;

        const formatYAxis = (value) => {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
        };

        const isCategoryMode = (this.state.weekly.data?.weekly_stack?.group_by === 'category');

        const chartDatasets = ds.map((d, i) => {
            const isOthers = (d._kind === 'category' ? d.category_id === 0 : d.product_id === 0);
            const color = isOthers ? OTHERS_COLOR : STACK_COLORS[i % STACK_COLORS.length];
            return {
                label: (d.code ? `[${d.code}] ` : '') + (d.name || ''),
                data: d.data || [],
                backgroundColor: color,
                borderColor: color,
                borderWidth: 0,
                stack: 'sales',
                _kind: d._kind || 'product',
                _antiquity_days: d.antiquity_days,
                _antiquity_source: d.antiquity_source,
                _product_id: d.product_id,
                _category_id: d.category_id || 0,
                _name: d.name,
            };
        });

        const weekTotals = (weeks.labels || []).map((_, i) =>
            chartDatasets.reduce((acc, d) => acc + (Number(d.data[i]) || 0), 0)
        );

        this._destroyChartByCanvasId('pdWeeklyStackCanvas');
        window.pdWeeklyStackObj = new Chart(canvas, {
            type: 'bar',
            data: { labels: weeks.labels || [], datasets: chartDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 24 } },
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const el = elements[0];
                    const dsObj = chartDatasets[el.datasetIndex];
                    if (!dsObj) { self.drillWeek(el.index); return; }
                    if (dsObj._kind === 'category' && dsObj._category_id) {
                        self._drillWeekCategory(el.index, dsObj._category_id, dsObj._name);
                    } else if (dsObj._product_id) {
                        self.drillWeek(el.index, dsObj._product_id, dsObj._name);
                    } else {
                        // Segmento "Otros": drill solo a items fuera del Top
                        self.drillWeek(el.index, null, null, true);
                    }
                },
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'right',
                        onClick: this._stackedLegendOnClick,
                        labels: {
                            boxWidth: 12,
                            font: { size: 11 },
                            generateLabels: this._stackedLegendWithPct(),
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#1e293b',
                        padding: 12,
                        displayColors: true,
                        filter: (item) => (item.raw || 0) !== 0,
                        callbacks: {
                            label: (c) => {
                                const dsObj = chartDatasets[c.datasetIndex];
                                const val = c.raw || 0;
                                let line = `${dsObj.label}: ${self.formatFullNumber(val)}`;
                                if (!isCategoryMode && dsObj._antiquity_days != null) {
                                    const yrs = (dsObj._antiquity_days / 365).toFixed(1);
                                    const src = dsObj._antiquity_source === 'reception'
                                        ? '1ra recepción' : 'alta';
                                    line += ` · Antig. ${dsObj._antiquity_days}d (${yrs}a, ${src})`;
                                }
                                return line;
                            },
                            footer: (items) => {
                                if (!items || !items.length) return '';
                                const sum = items.reduce((a, b) => a + (b.raw || 0), 0);
                                return `Total semana: ${self.formatFullNumber(sum)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, ticks: { callback: formatYAxis }, grid: { color: '#f1f5f9' } }
                }
            },
            plugins: [
                {
                    id: 'weeklyTotalLabels',
                    afterDatasetsDraw: (chart) => {
                        const { ctx, scales } = chart;
                        const xScale = scales.x;
                        const yScale = scales.y;
                        if (!xScale || !yScale) return;
                        ctx.save();
                        ctx.font = 'bold 12px sans-serif';
                        ctx.fillStyle = '#1e293b';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';
                        weekTotals.forEach((total, i) => {
                            if (!total) return;
                            const x = xScale.getPixelForValue(i);
                            const y = yScale.getPixelForValue(total);
                            ctx.fillText(self.formatCurrency(total), x, y - 6);
                        });
                        ctx.restore();
                    }
                },
                ...this._stackedPctLabelsPlugin(this.state.filters.show_pct),
            ]
        });
    }

    /**
     * Devuelve el color asociado a una fila del resumen por categoría según
     * su posición en el ranking (los primeros 8 usan la paleta del chart;
     * el resto cae en gris). Acepta el índice 0-based.
     */
    categoryColor(idx) {
        if (idx == null || idx < 0) return OTHERS_COLOR;
        if (idx < STACK_COLORS.length) return STACK_COLORS[idx];
        return OTHERS_COLOR;
    }

    // ===== Helpers de moneda =====
    _getCurrency() {
        const c = this.state.data?.currency || {};
        return {
            symbol: c.symbol || '$',
            position: c.position || 'before',
            decimal_places: (c.decimal_places ?? 2),
        };
    }
    _wrap(numStr, sign = "") {
        const c = this._getCurrency();
        return c.position === 'after' ? `${sign}${numStr} ${c.symbol}` : `${sign}${c.symbol} ${numStr}`;
    }
    formatFullNumber(value) {
        const c = this._getCurrency();
        const v = parseFloat(value) || 0;
        const numStr = v.toLocaleString(undefined, {
            minimumFractionDigits: c.decimal_places,
            maximumFractionDigits: c.decimal_places,
        });
        return this._wrap(numStr);
    }
    formatCurrency(value) {
        const c = this._getCurrency();
        const v = parseFloat(value) || 0;
        const sign = v < 0 ? "-" : "";
        const abs = Math.abs(v);
        let numStr;
        if (abs >= 1000000) numStr = (abs / 1000000).toFixed(2) + "M";
        else if (abs >= 1000) numStr = (abs / 1000).toFixed(1) + "K";
        else numStr = abs.toFixed(c.decimal_places);
        return this._wrap(numStr, sign);
    }
}

ProductDashboard.template = "dashboard_cross.product_dashboard";

registry.category("actions").add("dashboard_cross.product_dashboard", ProductDashboard);
