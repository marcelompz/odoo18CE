/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

// Paths to vendored assets (served por Odoo bajo /<module>/static/...)
const LIB = {
    jquery:     "/dashboard_cross/static/src/lib/jquery-3.7.1.min.js",
    chart:      "/dashboard_cross/static/src/lib/chart.umd.min.js",
    select2Js:  "/dashboard_cross/static/src/lib/select2.min.js",
    select2Css: "/dashboard_cross/static/src/lib/select2.min.css",
    tailwind:   "/dashboard_cross/static/src/lib/tailwind.min.css",
};

export class CommercialDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        
        // Calculate the first and last day of current month in YYYY-MM-DD
        const now = new Date();
        // Predeterminado: rango de 12 meses (inicio a fin), terminando en el mes actual.
        const firstDay = new Date(now.getFullYear(), now.getMonth() - 11, 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        
        const formatDate = (d) => {
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${d.getFullYear()}-${month}-${day}`;
        };

        this.state = useState({
            data: {
                currency: { symbol: '', name: '', position: 'before', decimal_places: 2 },
                kpis: {
                    total_sales: 0,
                    total_profit: 0,
                    avg_ticket: 0,
                    open_pipe: 0,
                    opp_count: 0,
                    conversion_rate: 0,
                },
                funnel: [],
                top_salespeople: [],
                customer_health: { new: 0, recurring: 0, lost: 0, avg_lifetime_value: 0 },
                product_portfolio: { top_sellers: [], high_margin: [], low_rotation: [] },
                payment_methods: { labels: [], cash: [], credit: [] },
                trends: { labels: [], current_year: [], last_year: [] },
                salesperson_analysis: {
                    labels: [], cash: [], credit: [], cash_qty: [], credit_qty: [],
                    new_cust: [], recurring_cust: [], new_cust_qty: [], recurring_cust_qty: [],
                    margins: [], distribution: [], distribution_qty: []
                },
                category_analysis: {
                    labels: [], revenue: [], revenue_qty: [], margins: [], rotation: []
                },
                revenue_composition: {
                    labels: [], revenue: [], cost: [], profit: []
                }
            },
            viewMode: 'amount', // 'amount' or 'quantity'
            filters: {
                date_from: formatDate(firstDay),
                date_to: formatDate(lastDay),
                product_id: "",
                category_id: "",
                partner_id: "",
                company_ids: [],   // INC-02: [] = todas (consolidado)
            },
            companies: [],         // opciones del selector (del backend)
            filterData: {
                products: [],
                categories: [],
                partners: []
            },
            showMobileFilters: false,
            showRangeCaption: true,   // leyenda de rango de fechas bajo cada gráfico
            loading: true,
        });

        onWillStart(async () => {
            // CSS de Tailwind precompilado (contiene las clases y el tema Odoo)
            try {
                await loadCSS(LIB.tailwind);
            } catch (e) {
                console.error("Failed to load Tailwind CSS", e);
            }

            // Cargar datasets de filtros en paralelo
            try {
                const [products, categories, partners] = await Promise.all([
                    this.orm.call("product.product", "search_read", [[["sale_ok", "=", true]]], { fields: ["id", "name"], limit: 50 }),
                    this.orm.call("product.category", "search_read", [[]], { fields: ["id", "name"] }),
                    this.orm.call("res.partner", "search_read", [[]], { fields: ["id", "name"], limit: 50 })
                ]);
                this.state.filterData.products = products;
                this.state.filterData.categories = categories;
                this.state.filterData.partners = partners;
            } catch (e) { console.error("Filter Data Error:", e); }
        });

        onMounted(async () => {
            // Todas las libs servidas localmente desde /dashboard_cross/static/src/lib
            try {
                if (!window.$) await loadJS(LIB.jquery);
                if (!window.Chart) await loadJS(LIB.chart);
            } catch (e) {
                console.error("Failed to load core libs", e);
            }

            // Select2 (JS + CSS), solo si no están ya disponibles
            if (window.$ && !window.$.fn.select2) {
                try {
                    await loadCSS(LIB.select2Css);
                    await loadJS(LIB.select2Js);
                } catch (e) {
                    console.error("Failed to load Select2", e);
                }
            }

            this.fetchDashboardData().then(() => {
                this.state.loading = false;
                setTimeout(() => {
                    if (window.$ && window.$.fn.select2) {
                        this.initSelect2();
                    }
                    this.renderCharts();
                }, 100);
            });
        });
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
        this.renderCharts();
    }

    initSelect2() {
        if (!window.$) return;
        setTimeout(() => {
            const productSelect = window.$('#filter_product_id');
            const partnerSelect = window.$('#filter_partner_id');
            const categorySelect = window.$('#filter_category_id');

            // Initialize and sync Product
            if (productSelect.length) {
                productSelect.select2({ width: '100%', placeholder: 'Todos', allowClear: true });
                if (this.state.filters.product_id) productSelect.val(this.state.filters.product_id).trigger('change.select2');
                productSelect.on('change', (e) => { 
                    this.state.filters.product_id = window.$(e.target).val() || ""; 
                    this.applyFilters();
                });
            }

            // Initialize and sync Partner
            if (partnerSelect.length) {
                partnerSelect.select2({ width: '100%', placeholder: 'Todos', allowClear: true });
                if (this.state.filters.partner_id) partnerSelect.val(this.state.filters.partner_id).trigger('change.select2');
                partnerSelect.on('change', (e) => { 
                    this.state.filters.partner_id = window.$(e.target).val() || ""; 
                    this.applyFilters();
                });
            }
            
            // Initialize and sync Category
            if (categorySelect.length) {
                categorySelect.select2({ width: '100%', placeholder: 'Todas', allowClear: true });
                if (this.state.filters.category_id) categorySelect.val(this.state.filters.category_id).trigger('change.select2');
                categorySelect.on('change', (e) => { 
                    this.state.filters.category_id = window.$(e.target).val() || ""; 
                    this.applyFilters();
                });
            }
        }, 300);
    }

    /**
     * Abre la ficha form de un registro en Odoo al hacer click en una fila del dashboard.
     * Usa action_service de Odoo para navegar en la misma pestaña.
     */
    openRecord(model, resId) {
        if (!model || !resId) return;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: resId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    // =================================================================
    // Drill-down: click en un monto del dashboard -> listado de facturas
    // =================================================================

    /** Construye el dominio base de facturas respetando los filtros actuales del dashboard. */
    _baseInvoiceDomain() {
        const f = this.state.filters;
        const d = [
            ['move_type', 'in', ['out_invoice', 'out_refund']],
            ['state', '=', 'posted'],
        ];
        if (f.date_from) d.push(['invoice_date', '>=', f.date_from]);
        if (f.date_to)   d.push(['invoice_date', '<=', f.date_to]);
        if (f.partner_id)  d.push(['partner_id', '=', parseInt(f.partner_id)]);
        if (f.product_id)  d.push(['invoice_line_ids.product_id', '=', parseInt(f.product_id)]);
        if (f.category_id) d.push(['invoice_line_ids.product_id.categ_id', '=', parseInt(f.category_id)]);
        return d;
    }

    /** Abre la vista custom de facturas con el dominio dado. */
    drillInvoices(extraDomain = [], title = "Detalle de Facturas", overrideDomain = null) {
        const domain = overrideDomain || [...this._baseInvoiceDomain(), ...extraDomain];
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: title,
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: {
                create: false,
                list_view_ref: 'dashboard_cross.view_dashboard_cross_invoice_drill_list',
            },
            target: 'current',
        });
    }

    /** Drill por vendedor (invoice_user_id). */
    drillByUser(uid, name) {
        if (!uid) return;
        this.drillInvoices(
            [['invoice_user_id', '=', uid]],
            `Facturas - Vendedor: ${name || ''}`.trim()
        );
    }

    /** Drill por cliente (partner_id). */
    drillByPartner(pid, name) {
        if (!pid) return;
        this.drillInvoices(
            [['partner_id', '=', pid]],
            `Facturas - Cliente: ${name || ''}`.trim()
        );
    }

    /** Drill por producto (invoice_line_ids.product_id). */
    drillByProduct(productId, name) {
        if (!productId) return;
        this.drillInvoices(
            [['invoice_line_ids.product_id', '=', productId]],
            `Facturas - Producto: ${name || ''}`.trim()
        );
    }

    /** Drill por mes (indice en months_ranges enviado por el backend). */
    drillByMonth(idx) {
        const ranges = this.state.data.months_ranges || [];
        if (!ranges[idx]) return this.drillInvoices([], "Detalle del Mes");
        const { start, end } = ranges[idx];
        const f = this.state.filters;
        const d = [
            ['move_type', 'in', ['out_invoice', 'out_refund']],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', start],
            ['invoice_date', '<=', end],
        ];
        if (f.partner_id)  d.push(['partner_id', '=', parseInt(f.partner_id)]);
        if (f.product_id)  d.push(['invoice_line_ids.product_id', '=', parseInt(f.product_id)]);
        if (f.category_id) d.push(['invoice_line_ids.product_id.categ_id', '=', parseInt(f.category_id)]);
        const label = (this.state.data?.trends?.labels || [])[idx] || '';
        this.drillInvoices([], `Facturas del mes ${label}`, d);
    }

    /**
     * Drill "En Negociación":
     *   - Presupuestos (state in draft/sent), o
     *   - Ventas confirmadas (state in sale/done) sin factura asociada.
     * Respeta filtros de fecha, cliente, producto y categoria.
     */
    drillQuotations() {
        const f = this.state.filters;
        const d = [
            '|',
                ['state', 'in', ['draft', 'sent']],
                '&', ['state', 'in', ['sale', 'done']],
                     ['invoice_ids', '=', false],
        ];
        if (f.date_from)  d.push(['date_order', '>=', f.date_from]);
        if (f.date_to)    d.push(['date_order', '<=', f.date_to + ' 23:59:59']);
        if (f.partner_id) d.push(['partner_id', '=', parseInt(f.partner_id)]);
        if (f.product_id) d.push(['order_line.product_id', '=', parseInt(f.product_id)]);
        if (f.category_id) d.push(['order_line.product_id.categ_id', '=', parseInt(f.category_id)]);
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'En Negociación (Presupuestos + Ventas sin facturar)',
            res_model: 'sale.order',
            views: [[false, 'list'], [false, 'form']],
            domain: d,
            context: { create: false },
            target: 'current',
        });
    }

    toggleMobileFilters() {
        this.state.showMobileFilters = !this.state.showMobileFilters;
    }

    /** Rango de fechas activo formateado (DD/MM/YYYY → DD/MM/YYYY) para la leyenda bajo los gráficos. */
    rangeLabel() {
        const fmt = (s) => {
            if (!s) return '';
            const p = s.split('-');
            return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : s;
        };
        return `${fmt(this.state.filters.date_from)} → ${fmt(this.state.filters.date_to)}`;
    }

    isCompanySelected(companyId) {
        const sel = this.state.filters.company_ids || [];
        return sel.length === 0 || sel.includes(companyId);
    }

    toggleCompany(companyId) {
        const all = (this.state.companies || []).map(c => c.id);
        const cur = new Set((this.state.filters.company_ids && this.state.filters.company_ids.length)
            ? this.state.filters.company_ids : all);
        if (cur.has(companyId)) cur.delete(companyId); else cur.add(companyId);
        this.state.filters.company_ids = (cur.size === 0 || cur.size === all.length)
            ? [] : all.filter(id => cur.has(id));
        this.applyFilters();
    }

    async applyFilters() {
        this.state.loading = true;

        if (window.$) {
            this.state.filters.product_id = (window.$('#filter_product_id').val() || window.$('#mobile_filter_product_id').val() || "");
            this.state.filters.category_id = (window.$('#filter_category_id').val() || window.$('#mobile_filter_category_id').val() || "");
            this.state.filters.partner_id = (window.$('#filter_partner_id').val() || window.$('#mobile_filter_partner_id').val() || "");
        }
        
        await this.fetchDashboardData();
        this.state.loading = false;
        this.state.showMobileFilters = false; // Close sidebar after applying
        
        setTimeout(() => {
            if (window.$ && window.$.fn.select2) {
                this.initSelect2();
            }
            this.renderCharts();
        }, 100);
    }

    async fetchDashboardData() {
        try {
            const cleanFilters = {
                date_from: this.state.filters.date_from || false,
                date_to: this.state.filters.date_to || false,
                product_id: this.state.filters.product_id ? parseInt(this.state.filters.product_id) : false,
                category_id: this.state.filters.category_id ? parseInt(this.state.filters.category_id) : false,
                partner_id: this.state.filters.partner_id ? parseInt(this.state.filters.partner_id) : false,
                company_ids: this.state.filters.company_ids || [],
            };

            const response = await this.orm.call(
                "dashboard_cross.api",
                "get_commercial_data",
                [cleanFilters]
            );
            if (response) {
                this.state.data = response;
                if (response.companies) this.state.companies = response.companies;
            }
        } catch (e) {
            console.error("Dashboard Fetch Error:", e);
        }
    }

    renderCharts() {
        if (!window.Chart) return;
        
        const isQty = this.state.viewMode === 'quantity';

        // Custom scale formatting for tooltips and axes
        const formatYAxis = (value) => {
            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
            return value;
        };

        // --- 1. Main Revenue Line Chart (Upgraded to Chart.js for professional aesthetics) ---
        const salesCanvas = document.getElementById('salesTrendCanvas');
        if (salesCanvas) {
            const trends = this.state.data?.trends || { labels: [], current_year: [], last_year: [] };
            
            if (window.salesTrendChartObj) window.salesTrendChartObj.destroy();
            window.salesTrendChartObj = new Chart(salesCanvas, {
                type: 'line',
                data: {
                    labels: trends.labels,
                    datasets: [
                        {
                            label: 'Actual',
                            data: trends.current_year,
                            borderColor: '#1c3d6e',
                            backgroundColor: 'rgba(1, 126, 132, 0.1)',
                            fill: true,
                            tension: 0.3,
                            borderWidth: 3,
                            pointRadius: 6,
                            pointBackgroundColor: '#fff',
                            pointBorderWidth: 3,
                            pointHoverRadius: 8,
                            pointHoverBackgroundColor: '#1c3d6e',
                            pointHoverBorderColor: '#fff',
                            pointHoverBorderWidth: 2,
                        },
                        {
                            label: 'Año Pasado',
                            data: trends.last_year,
                            borderColor: '#cbd5e1',
                            borderDash: [5, 5],
                            fill: false,
                            tension: 0.3,
                            borderWidth: 2,
                            pointRadius: 0, // Keep last year cleaner
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (evt, elements) => {
                        if (elements && elements.length) {
                            this.drillByMonth(elements[0].index);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#1e293b',
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            padding: 12,
                            displayColors: false,
                            callbacks: {
                                label: (c) => `Ventas: ${this.formatFullNumber(c.raw)} (click para ver facturas)`
                            }
                        }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { font: { size: 11, weight: '500' } } },
                        y: { 
                            beginAtZero: true,
                            grid: { color: '#f1f5f9' },
                            ticks: { 
                                callback: formatYAxis,
                                font: { size: 11 }
                            }
                        }
                    },
                    // Custom plugin to draw large labels on top of points
                    plugins: [{
                        id: 'customLabels',
                        afterDatasetsDraw: (chart) => {
                            const {ctx, data} = chart;
                            ctx.save();
                            ctx.font = 'bold 13px sans-serif';
                            ctx.fillStyle = '#1c3d6e';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';

                            chart.getDatasetMeta(0).data.forEach((p, i) => {
                                const val = data.datasets[0].data[i];
                                ctx.fillText(this.formatCurrency(val), p.x, p.y - 12);
                            });
                            ctx.restore();
                        }
                    }]
                }
            });
        }

        // --- 2. Chart.js Stacked Bar for Monthly Payment Methods ---
        const payCanvas = document.getElementById('paymentMethodCanvas');
        if (payCanvas) {
            const payData = this.state.data?.payment_methods || {
               labels: [], cash: [], credit: []
            };

            if (window.paymentMethodChartObj) window.paymentMethodChartObj.destroy();
            window.paymentMethodChartObj = new Chart(payCanvas, {
                type: 'bar',
                data: {
                    labels: payData.labels,
                    datasets: [
                        { label: 'Contado', data: payData.cash, backgroundColor: '#3B82F6' },
                        { label: 'Crédito', data: payData.credit, backgroundColor: '#c8992f' }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    onClick: (evt, elements) => {
                        if (elements && elements.length) {
                            this.drillByMonth(elements[0].index);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + this.formatCurrency(c.raw) + ' (' + this.formatFullNumber(c.raw) + ')' } }
                    },
                    scales: {
                        x: { stacked: true, grid: { display: false } },
                        y: { stacked: true, ticks: { callback: formatYAxis } }
                    }
                }
            });
        }

        // --- 2b. Chart.js Stacked Bar for Revenue Composition (Cost vs Profit) ---
        const compCanvas = document.getElementById('revenueCompositionCanvas');
        if (compCanvas) {
            const compData = this.state.data?.revenue_composition || {
                labels: [], revenue: [], cost: [], profit: []
            };

            if (window.revenueCompChartObj) window.revenueCompChartObj.destroy();
            window.revenueCompChartObj = new Chart(compCanvas, {
                type: 'bar',
                data: {
                    labels: compData.labels,
                    datasets: [
                        { label: 'Ganancia Bruta', data: compData.profit, backgroundColor: '#6366F1' },
                        { label: 'Costo', data: compData.cost, backgroundColor: '#9CA3AF' }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    onClick: (evt, elements) => {
                        if (elements && elements.length) {
                            this.drillByMonth(elements[0].index);
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (c) => c.dataset.label + ': ' + this.formatCurrency(c.raw) + ' (' + this.formatFullNumber(c.raw) + ')',
                            }
                        }
                    },
                    scales: {
                        x: { stacked: true, grid: { display: false } },
                        y: { stacked: true, ticks: { callback: formatYAxis } }
                    }
                }
            });
        }
        
        // Extract salesperson data
        const spData = this.state.data?.salesperson_analysis || {
            labels: [], cash: [], credit: [], cash_qty: [], credit_qty: [],
            new_cust: [], recurring_cust: [], new_cust_qty: [], recurring_cust_qty: [],
            margins: [], distribution: [], distribution_qty: []
        };
        const commonOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false, position: 'bottom' } } };

        // --- 3. Salesperson: Cash vs Credit ---
        const spCashCreditCanvas = document.getElementById('salespersonCashCreditCanvas');
        if (spCashCreditCanvas) {
            if (window.spCashCreditChartObj) window.spCashCreditChartObj.destroy();
            window.spCashCreditChartObj = new Chart(spCashCreditCanvas, {
                type: 'bar',
                data: {
                    labels: spData.labels,
                    datasets: [
                        { label: 'Contado', data: isQty ? spData.cash_qty : spData.cash, backgroundColor: '#3B82F6' },
                        { label: 'Crédito', data: isQty ? spData.credit_qty : spData.credit, backgroundColor: '#c8992f' }
                    ]
                },
                options: {
                    ...commonOptions,
                    plugins: { 
                        ...commonOptions.plugins, 
                        legend: { display: true, position: 'bottom' }, 
                        tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + (isQty ? c.raw.toLocaleString() : this.formatCurrency(c.raw) + ' (' + this.formatFullNumber(c.raw) + ')') } } 
                    },
                    scales: { 
                        x: { stacked: true }, 
                        y: { stacked: true, ticks: { callback: isQty ? null : formatYAxis } } 
                    }
                }
            });
        }

        // --- 4. Salesperson: New vs Recurring Customers ---
        const spNewRecurCanvas = document.getElementById('salespersonNewRecurringCanvas');
        if (spNewRecurCanvas) {
            if (window.spNewRecurChartObj) window.spNewRecurChartObj.destroy();
            window.spNewRecurChartObj = new Chart(spNewRecurCanvas, {
                type: 'bar',
                data: {
                    labels: spData.labels,
                    datasets: [
                        { label: 'Nuevos', data: isQty ? spData.new_cust_qty : spData.new_cust, backgroundColor: '#1c3d6e' },
                        { label: 'Recurrentes', data: isQty ? spData.recurring_cust_qty : spData.recurring_cust, backgroundColor: '#b7dada' }
                    ]
                },
                options: {
                    ...commonOptions,
                    plugins: { 
                        ...commonOptions.plugins, 
                        legend: { display: true, position: 'bottom' }, 
                        tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + (isQty ? c.raw.toLocaleString() : this.formatCurrency(c.raw) + ' (' + this.formatFullNumber(c.raw) + ')') } } 
                    },
                    scales: { 
                        x: { stacked: true }, 
                        y: { stacked: true, ticks: { callback: isQty ? null : formatYAxis } } 
                    }
                }
            });
        }

        // --- 5. Salesperson: Distribution Pie Chart ---
        const spPieCanvas = document.getElementById('salespersonPieCanvas');
        if (spPieCanvas) {
            if (window.spPieChartObj) window.spPieChartObj.destroy();
            window.spPieChartObj = new Chart(spPieCanvas, {
                type: 'doughnut',
                data: {
                    labels: spData.labels,
                    datasets: [{
                        data: isQty ? spData.distribution_qty : spData.distribution,
                        backgroundColor: ['#1c3d6e', '#c8992f', '#3B82F6', '#7ba3cc', '#F59E0B', '#10B981', '#6366F1', '#EC4899']
                    }]
                },
                options: {
                    ...commonOptions,
                    plugins: { 
                        ...commonOptions.plugins, 
                        legend: { display: true, position: 'right' }, 
                        tooltip: { callbacks: { label: (c) => c.label + ': ' + (isQty ? c.raw.toLocaleString() : this.formatCurrency(c.raw) + ' (' + this.formatFullNumber(c.raw) + ')') } } 
                    }
                }
            });
        }

        // --- 6. Salesperson: Average Margin Comparison ---
        const spMarginCanvas = document.getElementById('salespersonMarginCanvas');
        if (spMarginCanvas) {
            if (window.spMarginChartObj) window.spMarginChartObj.destroy();
            window.spMarginChartObj = new Chart(spMarginCanvas, {
                type: 'bar',
                data: {
                    labels: spData.labels,
                    datasets: [{
                        label: 'Margen Promedio (%)',
                        data: spData.margins,
                        backgroundColor: '#10B981', // Emerald green
                        borderRadius: 4
                    }]
                },
                options: {
                    ...commonOptions,
                    plugins: { ...commonOptions.plugins, tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + c.raw.toFixed(1) + '%' } } },
                    scales: {
                        y: { ticks: { callback: (val) => val + '%' }, suggestedMax: 100 }
                    }
                }
            });
        }
        
        // --- 7. Category Analysis ---
        const catData = this.state.data?.category_analysis || {
            labels: [], revenue: [], revenue_qty: [], margins: [], rotation: []
        };
        
        // 7a. Category Revenue Pie
        const catRevPieCanvas = document.getElementById('categoryRevenuePieCanvas');
        if (catRevPieCanvas) {
            if (window.catRevPieChartObj) window.catRevPieChartObj.destroy();
            window.catRevPieChartObj = new Chart(catRevPieCanvas, {
                type: 'pie',
                data: {
                    labels: catData.labels,
                    datasets: [{
                        data: isQty ? catData.revenue_qty : catData.revenue,
                        backgroundColor: ['#7ba3cc', '#1c3d6e', '#c8992f', '#3B82F6', '#10B981', '#F59E0B', '#6366F1']
                    }]
                },
                options: {
                    ...commonOptions,
                    plugins: { 
                        ...commonOptions.plugins, 
                        legend: { display: true, position: 'right' }, 
                        tooltip: { callbacks: { label: (c) => c.label + ': ' + (isQty ? c.raw.toLocaleString() : this.formatCurrency(c.raw) + ' (' + this.formatFullNumber(c.raw) + ')') } } 
                    }
                }
            });
        }
        
        // 7b. Category Margin Bar
        const catMarginBarCanvas = document.getElementById('categoryMarginBarCanvas');
        if (catMarginBarCanvas) {
            if (window.catMarginBarChartObj) window.catMarginBarChartObj.destroy();
            window.catMarginBarChartObj = new Chart(catMarginBarCanvas, {
                type: 'bar',
                data: {
                    labels: catData.labels,
                    datasets: [{
                        label: 'Margen (%)',
                        data: catData.margins,
                        backgroundColor: '#3B82F6',
                        borderRadius: 4
                    }]
                },
                options: {
                    ...commonOptions,
                    plugins: { ...commonOptions.plugins, tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + c.raw.toFixed(1) + '%' } } },
                    scales: {
                        y: { ticks: { callback: (val) => val + '%' }, suggestedMax: 100 }
                    }
                }
            });
        }

        // 7c. Category Rotation Bar (Horizontal)
        const catRotBarCanvas = document.getElementById('categoryRotationBarCanvas');
        if (catRotBarCanvas) {
            if (window.catRotBarChartObj) window.catRotBarChartObj.destroy();
            window.catRotBarChartObj = new Chart(catRotBarCanvas, {
                type: 'bar',
                data: {
                    labels: catData.labels,
                    datasets: [{
                        label: 'Unidades Vendidas',
                        data: catData.rotation,
                        backgroundColor: '#c8992f',
                        borderRadius: 4
                    }]
                },
                options: {
                    ...commonOptions,
                    indexAxis: 'y',
                    plugins: { ...commonOptions.plugins, tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + c.raw.toLocaleString() + ' ud' } } },
                    scales: {
                        x: { beginAtZero: true, ticks: { precision: 0 } },
                        y: { grid: { display: false } }
                    }
                }
            });
        }
    }

    /**
     * Currency helpers that respect the currency returned by the backend
     * (symbol, position, decimals).
     */
    _getCurrency() {
        const c = this.state.data?.currency || {};
        return {
            symbol: c.symbol || '$',
            position: c.position || 'before',
            decimal_places: (c.decimal_places ?? 2),
        };
    }

    _wrapWithSymbol(numStr, sign = "") {
        const c = this._getCurrency();
        if (c.position === 'after') {
            return `${sign}${numStr} ${c.symbol}`;
        }
        return `${sign}${c.symbol} ${numStr}`;
    }

    formatFullNumber(value) {
        const c = this._getCurrency();
        const v = parseFloat(value) || 0;
        const numStr = v.toLocaleString(undefined, {
            minimumFractionDigits: c.decimal_places,
            maximumFractionDigits: c.decimal_places,
        });
        return this._wrapWithSymbol(numStr);
    }

    formatCurrency(value) {
        const c = this._getCurrency();
        const v = parseFloat(value) || 0;
        const sign = v < 0 ? "-" : "";
        const absValue = Math.abs(v);
        let numStr;
        if (absValue >= 1000000) {
            numStr = (absValue / 1000000).toFixed(2) + "M";
        } else if (absValue >= 1000) {
            numStr = (absValue / 1000).toFixed(1) + "K";
        } else {
            numStr = absValue.toFixed(c.decimal_places);
        }
        return this._wrapWithSymbol(numStr, sign);
    }
}

CommercialDashboard.template = "dashboard_cross.commercial_dashboard";

registry.category("actions").add("dashboard_cross.commercial_dashboard", CommercialDashboard);
