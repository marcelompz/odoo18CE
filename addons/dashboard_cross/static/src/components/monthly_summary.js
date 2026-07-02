/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

const LIB = {
    chart:    "/dashboard_cross/static/src/lib/chart.umd.min.js",
    tailwind: "/dashboard_cross/static/src/lib/tailwind.min.css",
};

// Paleta corporativa Perfipar (navy / celeste / gris + acentos)
const MGR_COLORS = [
    '#1c3d6e', '#7ba3cc', '#8c919b', '#c8992f',
    '#2e7d44', '#5b8cc4', '#b0563b', '#46536b', '#9aa7bd', '#3a6ea5',
];

export class MonthlySummaryDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loading: true,
            showMobileFilters: false,
            showRangeCaption: true,
            filters: { preset: '12m', company_ids: [] },
            companies: [],
            data: {
                currency: { symbol: 'Gs.', name: 'PYG', position: 'before', decimal_places: 0 },
                period: { date_from: '', date_to: '', preset: '12m', months: 0 },
                months: { labels: [], ranges: [] },
                monthly_total: [],
                rows: [],
                totals: { total_period: 0, avg_month: 0, best_month: null, worst_month: null },
            },
        });

        onWillStart(async () => {
            try { await loadCSS(LIB.tailwind); } catch (e) {}
        });

        onMounted(async () => {
            try { if (!window.Chart) await loadJS(LIB.chart); } catch (e) {}
            await this.fetchData();
            this.state.loading = false;
            setTimeout(() => this.renderCharts(), 100);
        });

        onWillUnmount(() => {
            this._destroyChart('msEvolutionCanvas');
            window.msEvolutionObj = null;
        });
    }

    _destroyChart(id) {
        if (!window.Chart) return;
        const c = document.getElementById(id);
        if (!c) return;
        const existing = window.Chart.getChart ? window.Chart.getChart(c) : null;
        if (existing) { try { existing.destroy(); } catch (e) {} }
    }

    mgrColor(idx) { return MGR_COLORS[idx % MGR_COLORS.length]; }

    setPreset(value) {
        const valid = ['3m', '6m', '9m', '12m'];
        if (!valid.includes(value)) return;
        if (this.state.filters.preset === value) return;
        this.state.filters.preset = value;
        this.applyFilters();
    }

    toggleMobileFilters() { this.state.showMobileFilters = !this.state.showMobileFilters; }

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
        await this.fetchData();
        this.state.loading = false;
        this.state.showMobileFilters = false;
        setTimeout(() => this.renderCharts(), 100);
    }

    async fetchData() {
        try {
            const payload = { preset: this.state.filters.preset,
                              company_ids: this.state.filters.company_ids || [] };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_monthly_summary_data",
                [payload]
            );
            if (resp) {
                this.state.data = resp;
                if (resp.companies) this.state.companies = resp.companies;
            }
        } catch (e) {
            console.error("MonthlySummary fetch error:", e);
        }
    }

    /** Drill: abre facturas del vendedor en el período. */
    drillManager(uid, name) {
        if (!uid) return;
        const period = this.state.data?.period || {};
        const domain = [
            ['move_type', 'in', ['out_invoice', 'out_refund']],
            ['state', '=', 'posted'],
            ['invoice_user_id', '=', uid],
        ];
        if (period.date_from) domain.push(['invoice_date', '>=', period.date_from]);
        if (period.date_to)   domain.push(['invoice_date', '<=', period.date_to]);
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Facturas - ${name || ''}`.trim(),
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: { create: false },
            target: 'current',
        });
    }

    /** Drill por mes (todas las facturas del mes). */
    drillMonth(idx) {
        const ranges = this.state.data?.months?.ranges || [];
        if (!ranges[idx]) return;
        const { start, end } = ranges[idx];
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: `Facturas del mes ${(this.state.data?.months?.labels || [])[idx] || ''}`,
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['move_type', 'in', ['out_invoice', 'out_refund']],
                ['state', '=', 'posted'],
                ['invoice_date', '>=', start],
                ['invoice_date', '<=', end],
            ],
            context: { create: false },
            target: 'current',
        });
    }

    renderCharts() {
        if (!window.Chart) return;
        this.renderEvolutionChart();
    }

    /** Línea: evolución del total mensual. */
    renderEvolutionChart() {
        const canvas = document.getElementById('msEvolutionCanvas');
        if (!canvas) return;
        const labels = this.state.data?.months?.labels || [];
        const data = this.state.data?.monthly_total || [];
        if (!labels.length) { this._destroyChart('msEvolutionCanvas'); return; }
        const self = this;
        const formatY = (v) => {
            if (v >= 1000000000) return (v / 1000000000).toFixed(1) + 'B';
            if (v >= 1000000) return (v / 1000000).toFixed(0) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(0) + 'K';
            return v;
        };

        this._destroyChart('msEvolutionCanvas');
        window.msEvolutionObj = new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Total mensual (Gs.)',
                    data,
                    borderColor: '#1c3d6e',
                    backgroundColor: 'rgba(28, 61, 110, 0.10)',
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#1c3d6e',
                    pointBorderWidth: 2,
                    pointHoverRadius: 7,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 28 } },
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    self.drillMonth(elements[0].index);
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => `Total: ${self.formatFullNumber(c.raw || 0)}`,
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { callback: formatY }, grid: { color: '#f1f5f9' } }
                }
            },
            plugins: [{
                id: 'monthlyDataLabels',
                afterDatasetsDraw: (chart) => {
                    const { ctx, scales } = chart;
                    if (!scales.x || !scales.y) return;
                    ctx.save();
                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillStyle = '#1c3d6e';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    data.forEach((v, i) => {
                        if (!v) return;
                        const x = scales.x.getPixelForValue(i);
                        const y = scales.y.getPixelForValue(v);
                        ctx.fillText(self.formatNumberPlain(v), x, y - 10);
                    });
                    ctx.restore();
                }
            }]
        });
    }

    _getCurrency() {
        const c = this.state.data?.currency || {};
        return {
            symbol: c.symbol || 'Gs.',
            position: c.position || 'before',
            decimal_places: (c.decimal_places ?? 0),
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
    formatNumberPlain(value) {
        const v = parseFloat(value) || 0;
        return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
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
}

MonthlySummaryDashboard.template = "dashboard_cross.monthly_summary_dashboard";

registry.category("actions").add("dashboard_cross.monthly_summary_dashboard", MonthlySummaryDashboard);
