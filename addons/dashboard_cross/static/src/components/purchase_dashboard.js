/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

const LIB = {
    chart:    "/dashboard_cross/static/src/lib/chart.umd.min.js",
    tailwind: "/dashboard_cross/static/src/lib/tailwind.min.css",
};

// Paleta categorial igual a la del dashboard de Productos (consistencia visual)
const STACK_COLORS = [
    '#1c3d6e', '#c8992f', '#7ba3cc', '#3B82F6',
    '#10B981', '#F59E0B', '#6366F1', '#EC4899',
];
const OTHERS_COLOR = '#CBD5E1';

export class PurchaseDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loading: true,
            showMobileFilters: false,
            showRangeCaption: true,
            filters: {
                preset: '12m',  // '3m' | '6m' | '9m' | '12m'
                show_pct: true,
                // Selector de compañía: [] = todas (suma todo).
                company_ids: [],
                // Check "Impuesto incluido" (IVA). Afecta la línea de ventas; las
                // compras son costo (valorización) y no llevan IVA.
                tax_included: false,
            },
            // Opciones del selector de compañía (llegan del backend).
            companies: [],
            ui: {
                compareWithSales: true,  // mostrar línea de ventas en el chart mensual
                topProductsDetail: false, // tabla colapsable del top productos
            },
            data: {
                currency: { symbol: '', name: '', position: 'before', decimal_places: 2 },
                period: { date_from: '', date_to: '', preset: '6m' },
                kpis: { total_invested: 0, invoice_count: 0, supplier_count: 0, product_count: 0 },
                monthly: { labels: [], ranges: [], purchases: [], sales: [] },
                top_suppliers: [],
                top_products: [],
                category_summary: [],
            },
        });

        onWillStart(async () => {
            try { await loadCSS(LIB.tailwind); } catch (e) { console.error("Tailwind CSS", e); }
        });

        onMounted(async () => {
            try { if (!window.Chart) await loadJS(LIB.chart); }
            catch (e) { console.error("Chart.js", e); }

            await this.fetchData();
            this.state.loading = false;
            setTimeout(() => this.renderCharts(), 100);
        });

        onWillUnmount(() => {
            this._destroyChartByCanvasId('pcMonthlyCanvas');
            this._destroyChartByCanvasId('pcSuppliersCanvas');
            this._destroyChartByCanvasId('pcCategoryCanvas');
            this._destroyChartByCanvasId('pcTopProductsCanvas');
            window.pcMonthlyObj = null;
            window.pcSuppliersObj = null;
            window.pcCategoryObj = null;
            window.pcTopProductsObj = null;
        });
    }

    _destroyChartByCanvasId(id) {
        if (!window.Chart) return;
        const c = document.getElementById(id);
        if (!c) return;
        const existing = window.Chart.getChart ? window.Chart.getChart(c) : null;
        if (existing) { try { existing.destroy(); } catch (e) {} }
    }

    setPreset(value) {
        const valid = ['3m', '6m', '9m', '12m'];
        if (!valid.includes(value)) return;
        if (this.state.filters.preset === value) return;
        this.state.filters.preset = value;
        this.applyFilters();
    }

    /** Check "Impuesto incluido" (IVA): afecta la línea de ventas. */
    toggleTaxIncluded() {
        this.state.filters.tax_included = !this.state.filters.tax_included;
        this.applyFilters();
    }

    /** ¿Está marcada esta compañía? ([] = todas marcadas = suma todo). */
    isCompanySelected(companyId) {
        const sel = this.state.filters.company_ids || [];
        return sel.length === 0 || sel.includes(companyId);
    }

    /** Marca/desmarca una compañía; [] = todas (suma todo). */
    toggleCompany(companyId) {
        const all = (this.state.companies || []).map(c => c.id);
        const current = new Set(
            (this.state.filters.company_ids && this.state.filters.company_ids.length)
                ? this.state.filters.company_ids
                : all
        );
        if (current.has(companyId)) current.delete(companyId);
        else current.add(companyId);
        if (current.size === 0 || current.size === all.length) {
            this.state.filters.company_ids = [];
        } else {
            this.state.filters.company_ids = all.filter(id => current.has(id));
        }
        this.applyFilters();
    }

    toggleCompareWithSales() {
        this.state.ui.compareWithSales = !this.state.ui.compareWithSales;
        setTimeout(() => this.renderMonthlyChart(), 30);
    }

    toggleShowPct() {
        this.state.filters.show_pct = !this.state.filters.show_pct;
        this.renderCharts();
    }

    toggleTopProductsDetail() {
        this.state.ui.topProductsDetail = !this.state.ui.topProductsDetail;
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
                company_ids: this.state.filters.company_ids || [],
                tax_included: this.state.filters.tax_included || false,
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_purchase_dashboard_data",
                [payload]
            );
            if (resp) {
                this.state.data = resp;
                if (resp.companies) this.state.companies = resp.companies;
            }
        } catch (e) {
            console.error("PurchaseDashboard fetch error:", e);
        }
    }

    /**
     * Dominio base de las CAPAS DE VALORIZACIÓN que componen las compras:
     * mercadería recibida de proveedor ligada a OC, neto de devoluciones
     * (recepción proveedor→interno y devolución interno→proveedor), state done.
     * Es exactamente lo que suman las barras (no las facturas).
     * `extra` agrega filtros (producto/categoría/proveedor/fechas).
     */
    _receivedLayerDomain(extra) {
        // Recepciones de mercadería de OC confirmada (entrada proveedor→interno).
        const dom = [
            ['stock_move_id.purchase_line_id', '!=', false],
            ['stock_move_id.state', '=', 'done'],
            ['stock_move_id.location_id.usage', '=', 'supplier'],
            ['stock_move_id.location_dest_id.usage', '=', 'internal'],
            ['stock_move_id.purchase_line_id.order_id.state', '=', 'purchase'],
            ['product_id.type', '=', 'consu'],
            ['product_id.is_storable', '=', true],
        ];
        const cids = this.state.filters.company_ids || [];
        if (cids.length) dom.push(['company_id', 'in', cids]);
        return dom.concat(extra || []);
    }

    /** Abre la vista de capas de valorización (recepciones) con el dominio dado. */
    _openReceivedLayers(name, extra) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: 'stock.valuation.layer',
            views: [[false, 'list'], [false, 'form']],
            domain: this._receivedLayerDomain(extra),
            context: { create: false },
            target: 'current',
        });
    }

    /** Rango de fechas del período como filtro de create_date (incluye día final). */
    _periodDateLeaves() {
        const period = this.state.data?.period || {};
        const leaves = [];
        if (period.date_from) leaves.push(['create_date', '>=', period.date_from + ' 00:00:00']);
        if (period.date_to)   leaves.push(['create_date', '<=', period.date_to + ' 23:59:59']);
        return leaves;
    }

    /** Drill al proveedor: recepciones de mercadería de ese proveedor (vía OC). */
    drillSupplier(partnerId, name) {
        if (!partnerId) return;
        this._openReceivedLayers(
            `Recepciones de mercadería - ${name || ''}`.trim(),
            [['stock_move_id.purchase_line_id.order_id.partner_id', '=', partnerId]]
                .concat(this._periodDateLeaves()));
    }

    /** Drill al producto: recepciones valorizadas de ese producto. */
    drillProduct(productId, name) {
        if (!productId) return;
        this._openReceivedLayers(
            `Recepciones - ${name || ''}`.trim(),
            [['product_id', '=', productId]].concat(this._periodDateLeaves()));
    }

    /** Drill a categoría: recepciones valorizadas del rubro. */
    drillCategory(catId, name) {
        if (!catId) return;
        this._openReceivedLayers(
            `Recepciones - Cat. ${name || ''}`.trim(),
            [['product_id.categ_id', '=', catId]].concat(this._periodDateLeaves()));
    }

    /** Drill por mes: recepciones valorizadas del mes (lo que suma la barra). */
    drillMonth(idx) {
        const ranges = this.state.data?.monthly?.ranges || [];
        if (!ranges[idx]) return;
        const { start, end } = ranges[idx];
        this._openReceivedLayers(
            `Compras del mes ${(this.state.data?.monthly?.labels || [])[idx] || ''}`,
            [['create_date', '>=', start + ' 00:00:00'],
             ['create_date', '<=', end + ' 23:59:59']]);
    }

    // ============================================================
    // Renders
    // ============================================================
    renderCharts() {
        if (!window.Chart) return;
        this.renderMonthlyChart();
        this.renderSuppliersChart();
        this.renderCategoryChart();
        this.renderTopProductsChart();
    }

    renderMonthlyChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pcMonthlyCanvas');
        if (!canvas) return;
        const m = this.state.data?.monthly || { labels: [], purchases: [], sales: [] };
        if (!m.labels.length) { this._destroyChartByCanvasId('pcMonthlyCanvas'); return; }
        const self = this;
        const formatY = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
            return v;
        };

        const datasets = [{
            type: 'bar',
            label: 'Compras',
            data: m.purchases || [],
            backgroundColor: '#c8992f',
            borderRadius: 4,
        }];
        if (this.state.ui.compareWithSales) {
            datasets.push({
                type: 'line',
                label: 'Ventas',
                data: m.sales || [],
                borderColor: '#1c3d6e',
                backgroundColor: 'rgba(1, 126, 132, 0.08)',
                borderWidth: 3,
                tension: 0.3,
                pointRadius: 5,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#1c3d6e',
                pointBorderWidth: 2,
                fill: false,
                order: 0,
            });
        }

        // Totales por mes para label encima de la barra
        const purchasesArr = m.purchases || [];

        this._destroyChartByCanvasId('pcMonthlyCanvas');
        window.pcMonthlyObj = new Chart(canvas, {
            type: 'bar',
            data: { labels: m.labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 24 } },
                interaction: { mode: 'index', intersect: false },
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    self.drillMonth(elements[0].index);
                },
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => {
                                const v = c.raw || 0;
                                return `${c.dataset.label}: ${self.formatFullNumber(v)}`;
                            },
                            footer: (items) => {
                                if (!items || items.length < 2) return '';
                                const purchase = items.find(i => i.dataset.type === 'bar')?.raw || 0;
                                const sale = items.find(i => i.dataset.type === 'line')?.raw || 0;
                                if (purchase > 0 && sale > 0) {
                                    const ratio = (sale / purchase * 100).toFixed(0);
                                    return `Ventas / Compras: ${ratio}%`;
                                }
                                return '';
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { callback: formatY }, grid: { color: '#f1f5f9' } }
                }
            },
            plugins: [{
                id: 'monthlyPurchasesLabels',
                afterDatasetsDraw: (chart) => {
                    const { ctx, scales } = chart;
                    if (!scales.x || !scales.y) return;
                    ctx.save();
                    ctx.font = 'bold 12px sans-serif';
                    ctx.fillStyle = '#1e293b';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    purchasesArr.forEach((v, i) => {
                        if (!v) return;
                        const x = scales.x.getPixelForValue(i);
                        const y = scales.y.getPixelForValue(v);
                        ctx.fillText(self.formatCurrency(v), x, y - 6);
                    });
                    ctx.restore();
                }
            }]
        });
    }

    renderSuppliersChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pcSuppliersCanvas');
        if (!canvas) return;
        const items = this.state.data?.top_suppliers || [];
        if (!items.length) { this._destroyChartByCanvasId('pcSuppliersCanvas'); return; }
        const self = this;
        const formatY = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
            return v;
        };

        const labels = items.map(s => (s.name || '').length > 32 ? (s.name.slice(0, 30) + '…') : (s.name || ''));
        const data = items.map(s => s.amount || 0);

        this._destroyChartByCanvasId('pcSuppliersCanvas');
        window.pcSuppliersObj = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Monto neto comprado',
                    data,
                    backgroundColor: '#c8992f',
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const s = items[elements[0].index];
                    if (s) self.drillSupplier(s.id, s.name);
                },
                onHover: (event, els) => {
                    const t = event?.native?.target;
                    if (t && t.style) t.style.cursor = (els && els.length) ? 'pointer' : 'default';
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            title: (ctx) => (items[ctx[0].dataIndex] || {}).name || '',
                            label: (c) => `Comprado: ${self.formatFullNumber(c.raw || 0)}`,
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { callback: formatY } },
                    y: { grid: { display: false }, ticks: { font: { size: 11 } } }
                }
            }
        });
    }

    renderCategoryChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pcCategoryCanvas');
        if (!canvas) return;
        const summary = this.state.data?.category_summary || [];
        if (!summary.length) { this._destroyChartByCanvasId('pcCategoryCanvas'); return; }
        const labels = summary.map(c => c.name);
        const data = summary.map(c => c.amount || 0);
        const colors = summary.map((_, i) => i < STACK_COLORS.length ? STACK_COLORS[i] : OTHERS_COLOR);
        const total = data.reduce((s, v) => s + v, 0);
        const self = this;
        const showPct = this.state.filters.show_pct;

        this._destroyChartByCanvasId('pcCategoryCanvas');
        window.pcCategoryObj = new Chart(canvas, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }] },
            plugins: showPct ? [{
                id: 'pctLabels',
                afterDatasetsDraw: (chart) => {
                    const { ctx } = chart;
                    const meta = chart.getDatasetMeta(0);
                    if (!meta || !meta.data) return;
                    ctx.save();
                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillStyle = '#fff';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.shadowColor = 'rgba(0,0,0,0.35)';
                    ctx.shadowBlur = 2;
                    meta.data.forEach((arc, i) => {
                        const v = Number(data[i] || 0);
                        if (total <= 0) return;
                        const pct = v / total * 100;
                        if (pct < 3) return;
                        const angle = (arc.startAngle + arc.endAngle) / 2;
                        const r = (arc.innerRadius + arc.outerRadius) / 2;
                        const x = arc.x + Math.cos(angle) * r;
                        const y = arc.y + Math.sin(angle) * r;
                        ctx.fillText(`${pct.toFixed(0)}%`, x, y);
                    });
                    ctx.restore();
                }
            }] : [],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const c = summary[elements[0].index];
                    if (c && c.category_id) self.drillCategory(c.category_id, c.name);
                },
                onHover: (event, els) => {
                    const t = event?.native?.target;
                    if (t && t.style) t.style.cursor = (els && els.length) ? 'pointer' : 'default';
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => {
                                const item = summary[c.dataIndex] || {};
                                const pct = total > 0 ? (c.raw / total * 100).toFixed(1) : '0.0';
                                return [
                                    `${item.name}: ${self.formatFullNumber(c.raw || 0)} · ${pct}%`,
                                    `${item.product_count || 0} SKUs · ${(item.qty || 0).toLocaleString()} u`,
                                ];
                            }
                        }
                    }
                }
            }
        });
    }

    renderTopProductsChart() {
        if (!window.Chart) return;
        const canvas = document.getElementById('pcTopProductsCanvas');
        if (!canvas) return;
        const items = (this.state.data?.top_products || []).slice(0, 10);
        if (!items.length) { this._destroyChartByCanvasId('pcTopProductsCanvas'); return; }
        const self = this;
        const formatY = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
            return v;
        };

        const labels = items.map(p => {
            const code = p.code ? `[${p.code}] ` : '';
            const name = (p.name || '').length > 32 ? (p.name.slice(0, 30) + '…') : (p.name || '');
            return code + name;
        });
        const data = items.map(p => p.amount || 0);

        this._destroyChartByCanvasId('pcTopProductsCanvas');
        window.pcTopProductsObj = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Monto comprado',
                    data,
                    backgroundColor: '#7ba3cc',
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const it = items[elements[0].index];
                    if (it) self.drillProduct(it.id, it.name);
                },
                onHover: (event, els) => {
                    const t = event?.native?.target;
                    if (t && t.style) t.style.cursor = (els && els.length) ? 'pointer' : 'default';
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            title: (ctx) => (items[ctx[0].dataIndex] || {}).name || '',
                            label: (c) => {
                                const it = items[c.dataIndex] || {};
                                return [
                                    `Comprado: ${self.formatFullNumber(c.raw || 0)}`,
                                    `Cantidad: ${(it.qty || 0).toLocaleString()}`,
                                    `Categoría: ${it.category || '—'}`,
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { callback: formatY } },
                    y: { grid: { display: false }, ticks: { font: { size: 11 } } }
                }
            }
        });
    }

    // ============================================================
    // Currency helpers
    // ============================================================
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

    categoryColor(idx) {
        if (idx == null || idx < 0) return OTHERS_COLOR;
        if (idx < STACK_COLORS.length) return STACK_COLORS[idx];
        return OTHERS_COLOR;
    }
}

PurchaseDashboard.template = "dashboard_cross.purchase_dashboard";

registry.category("actions").add("dashboard_cross.purchase_dashboard", PurchaseDashboard);
