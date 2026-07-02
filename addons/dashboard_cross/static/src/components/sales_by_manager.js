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

export class SalesByManagerDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        const now = new Date();
        const y = now.getFullYear();
        // Predeterminado: rango de 12 meses (inicio a fin), terminando en el mes actual.
        const startD = new Date(y, now.getMonth() - 11, 1);
        const endD = new Date(y, now.getMonth() + 1, 0);
        const iso = (d) => `${d.getFullYear()}-${this._pad(d.getMonth() + 1)}-${this._pad(d.getDate())}`;
        this.state = useState({
            loading: true,
            showMobileFilters: false,
            showRangeCaption: true,
            filters: {
                year: y,
                monthsSelected: [],   // el rango de 12 meses cruza años; sin chips resaltados
                date_from: iso(startD),
                date_to: iso(endD),
                company_ids: [],      // INC-02: [] = todas (consolidado)
            },
            companies: [],
            data: this._emptyData(),
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
            this._destroyChart('sbmInformeVentasCanvas');
            this._destroyChart('sbmComparativoCanvas');
            this._destroyChart('sbmParticipacionCanvas');
            window.sbmInformeVentasObj = null;
            window.sbmComparativoObj = null;
            window.sbmParticipacionObj = null;
        });
    }

    _emptyData() {
        return {
            currency: { symbol: 'Gs.', name: 'PYG', position: 'before', decimal_places: 0 },
            period: { year: 0, month: 0, date_from: '', date_to: '', is_current_month: false },
            managers: [],
            daily_table: { days: [], labels: [], rows: [], total_per_day: [] },
            totals: { total_gs: 0, total_usd: 0 },
            comparative_quarter: { current_label: '', previous_label: '', current_total: 0, previous_total: 0, change_pct: 0 },
            projection: {
                total_days_month: 0, days_elapsed: 0, progress_pct: 0,
                projection_total: 0, projection_total_usd: 0, by_manager: [],
            },
            participation: [],
        };
    }

    _destroyChart(id) {
        if (!window.Chart) return;
        const c = document.getElementById(id);
        if (!c) return;
        const existing = window.Chart.getChart ? window.Chart.getChart(c) : null;
        if (existing) { try { existing.destroy(); } catch (e) {} }
    }

    mgrColor(idx) { return MGR_COLORS[idx % MGR_COLORS.length]; }

    _pad(n) { return String(n).padStart(2, '0'); }

    /** Rango activo formateado (DD/MM/YYYY → DD/MM/YYYY) para la leyenda bajo los gráficos. */
    rangeLabel() {
        const fmt = (s) => {
            if (!s) return '';
            const p = String(s).split('-');
            return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : s;
        };
        const per = (this.state.data && this.state.data.period) || {};
        return `${fmt(per.date_from)} → ${fmt(per.date_to_data || per.date_to)}`;
    }

    /** Recalcula date_from/date_to a partir de los meses seleccionados (mismo año). */
    _recomputeRange() {
        const y = this.state.filters.year;
        const ms = [...(this.state.filters.monthsSelected || [])].sort((a, b) => a - b);
        if (!ms.length) return;
        const minM = ms[0], maxM = ms[ms.length - 1];
        const lastDay = new Date(y, maxM, 0).getDate();
        this.state.filters.date_from = `${y}-${this._pad(minM)}-01`;
        this.state.filters.date_to = `${y}-${this._pad(maxM)}-${this._pad(lastDay)}`;
    }

    isMonthSelected(m) {
        return (this.state.filters.monthsSelected || []).includes(m);
    }

    setYear(year) {
        const y = parseInt(year) || new Date().getFullYear();
        if (this.state.filters.year === y) return;
        this.state.filters.year = y;
        this._recomputeRange();
        this.applyFilters();
    }

    /** Toggle de un chip de mes. Mantiene al menos uno seleccionado. */
    toggleMonth(m) {
        const arr = this.state.filters.monthsSelected || [];
        const i = arr.indexOf(m);
        if (i >= 0) {
            if (arr.length > 1) arr.splice(i, 1);
        } else {
            arr.push(m);
        }
        this.state.filters.monthsSelected = [...arr].sort((a, b) => a - b);
        this._recomputeRange();
        this.applyFilters();
    }

    /** El usuario editó Fecha Desde/Hasta a mano: resalta los meses del rango si es el mismo año. */
    onRangeChange() {
        const df = this.state.filters.date_from;
        const dt = this.state.filters.date_to;
        if (df && dt) {
            const [ay, am] = df.split('-').map(Number);
            const [by, bm] = dt.split('-').map(Number);
            if (ay === by) {
                this.state.filters.year = ay;
                const months = [];
                for (let mm = Math.min(am, bm); mm <= Math.max(am, bm); mm++) months.push(mm);
                this.state.filters.monthsSelected = months;
            } else {
                this.state.filters.monthsSelected = [];
            }
        }
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
            const payload = {
                date_from: this.state.filters.date_from,
                date_to: this.state.filters.date_to,
                company_ids: this.state.filters.company_ids || [],
            };
            const resp = await this.orm.call(
                "dashboard_cross.api",
                "get_sales_by_manager_data",
                [payload]
            );
            if (resp) {
                this.state.data = resp;
                if (resp.companies) this.state.companies = resp.companies;
            }
        } catch (e) {
            console.error("SalesByManager fetch error:", e);
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

    // ============================================================
    // Renders
    // ============================================================
    renderCharts() {
        if (!window.Chart) return;
        this.renderInformeVentasChart();
        this.renderComparativoChart();
        this.renderParticipacionChart();
    }

    /** Stacked bar: informe de ventas diario por vendedor. */
    renderInformeVentasChart() {
        const canvas = document.getElementById('sbmInformeVentasCanvas');
        if (!canvas) return;
        const dt = this.state.data?.daily_table || { labels: [], rows: [] };
        if (!dt.labels.length) { this._destroyChart('sbmInformeVentasCanvas'); return; }
        const self = this;
        const formatY = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
            return v;
        };
        const datasets = dt.rows.map((r, i) => ({
            label: r.name,
            data: r.amounts,
            backgroundColor: self.mgrColor(i),
            stack: 's',
            borderRadius: 2,
        }));

        this._destroyChart('sbmInformeVentasCanvas');
        window.sbmInformeVentasObj = new Chart(canvas, {
            type: 'bar',
            data: { labels: dt.labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => `${c.dataset.label}: ${self.formatFullNumber(c.raw || 0)}`,
                            footer: (items) => {
                                const total = items.reduce((s, i) => s + (i.raw || 0), 0);
                                return `Total: ${self.formatFullNumber(total)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, ticks: { callback: formatY }, grid: { color: '#f1f5f9' } }
                }
            }
        });
    }

    /** Bar: comparativo trimestre actual vs anterior. */
    renderComparativoChart() {
        const canvas = document.getElementById('sbmComparativoCanvas');
        if (!canvas) return;
        const cq = this.state.data?.comparative_quarter || {};
        if (!cq.current_label) { this._destroyChart('sbmComparativoCanvas'); return; }
        const self = this;
        const formatY = (v) => {
            if (v >= 1000000) return (v / 1000000).toFixed(0) + 'M';
            if (v >= 1000) return (v / 1000).toFixed(0) + 'K';
            return v;
        };

        this._destroyChart('sbmComparativoCanvas');
        window.sbmComparativoObj = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: [cq.previous_label, cq.current_label],
                datasets: [{
                    data: [cq.previous_total, cq.current_total],
                    backgroundColor: ['#1c3d6e', '#7ba3cc'],
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 24 } },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        callbacks: { label: (c) => self.formatFullNumber(c.raw || 0) }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { callback: formatY }, grid: { color: '#f1f5f9' } }
                }
            },
            plugins: [{
                id: 'compLabel',
                afterDatasetsDraw: (chart) => {
                    const { ctx, scales } = chart;
                    const vals = [cq.previous_total, cq.current_total];
                    ctx.save();
                    ctx.font = 'bold 12px sans-serif';
                    ctx.fillStyle = '#1e293b';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    vals.forEach((v, i) => {
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

    /** Donut: participación por vendedor. */
    renderParticipacionChart() {
        const canvas = document.getElementById('sbmParticipacionCanvas');
        if (!canvas) return;
        const p = this.state.data?.participation || [];
        if (!p.length) { this._destroyChart('sbmParticipacionCanvas'); return; }
        const self = this;
        const labels = p.map(x => x.name);
        const data = p.map(x => x.amount);
        const colors = p.map((_, i) => self.mgrColor(i));
        const total = data.reduce((s, v) => s + v, 0);
        const totalGs = this.state.data?.totals?.total_gs || 0;

        this._destroyChart('sbmParticipacionCanvas');
        window.sbmParticipacionObj = new Chart(canvas, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }] },
            plugins: [
                {
                    id: 'centerText',
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
                        ctx.fillText('TOTAL VENTAS', cx, cy - 16);
                        ctx.font = 'bold 18px sans-serif';
                        ctx.fillStyle = '#1e293b';
                        ctx.fillText(self.formatCurrency(totalGs), cx, cy + 4);
                        ctx.font = '11px sans-serif';
                        ctx.fillStyle = '#64748b';
                        ctx.fillText('Gs.', cx, cy + 22);
                        ctx.restore();
                    }
                },
                {
                    id: 'donutPct',
                    afterDatasetsDraw: (chart) => {
                        const ctx = chart.ctx;
                        const meta = chart.getDatasetMeta(0);
                        if (!meta || !meta.data) return;
                        ctx.save();
                        ctx.font = 'bold 12px sans-serif';
                        ctx.fillStyle = '#fff';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.shadowColor = 'rgba(0,0,0,0.35)';
                        ctx.shadowBlur = 2;
                        meta.data.forEach((arc, i) => {
                            const v = Number(data[i] || 0);
                            const pct = total > 0 ? (v / total * 100) : 0;
                            if (pct < 4) return;
                            const angle = (arc.startAngle + arc.endAngle) / 2;
                            const r = (arc.innerRadius + arc.outerRadius) / 2;
                            const x = arc.x + Math.cos(angle) * r;
                            const y = arc.y + Math.sin(angle) * r;
                            ctx.fillText(`${pct.toFixed(0)}%`, x, y);
                        });
                        ctx.restore();
                    }
                }
            ],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                onClick: (evt, elements) => {
                    if (!elements || !elements.length) return;
                    const item = p[elements[0].index];
                    if (item) self.drillManager(item.id, item.name);
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (c) => {
                                const item = p[c.dataIndex] || {};
                                return `${item.name}: ${self.formatFullNumber(c.raw || 0)} (${item.pct.toFixed(1)}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // ============================================================
    // Helpers de moneda y formato
    // ============================================================
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
    formatNumberPlain(value) {
        const v = parseFloat(value) || 0;
        return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    }
}

SalesByManagerDashboard.template = "dashboard_cross.sales_by_manager_dashboard";

registry.category("actions").add("dashboard_cross.sales_by_manager_dashboard", SalesByManagerDashboard);
