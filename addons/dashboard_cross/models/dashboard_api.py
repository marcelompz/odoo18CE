from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta

# Abreviaturas de meses en español (independiente del locale del servidor)
MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
            'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _month_label_es(d):
    """Etiqueta de mes en español tipo 'jul-25' (independiente del locale)."""
    return '%s-%02d' % (MESES_ES[d.month - 1], d.year % 100)


class DashboardCrossAPI(models.AbstractModel):
    """
    Dashboard Cross - API de datos consolidada.

    FUENTE DE DATOS: Facturas de cliente POSTEADAS (account.move)
        - move_type in ('out_invoice', 'out_refund')
        - state = 'posted'
        - out_refund (notas de crédito) resta del total.

    Todas las cifras monetarias son IVA INCLUIDO (amount_total / price_total).
    Se expresan en la moneda de la compañía activa.
    """
    _name = 'dashboard_cross.api'
    _description = 'Dashboard Cross Data API'

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _as_date(self, value, default):
        if not value:
            return default
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return fields.Date.from_string(value[:10])
            except Exception:
                return default
        return default

    def _day_start(self, d):
        return datetime.datetime.combine(d, datetime.time.min)

    def _day_end(self, d):
        return datetime.datetime.combine(d, datetime.time.max)

    def _convert_amount(self, amount, from_currency, to_currency, company, date):
        if not amount:
            return 0.0
        if from_currency and from_currency != to_currency:
            return from_currency._convert(amount, to_currency, company,
                                          date or fields.Date.today())
        return amount

    def _move_amount_in_company(self, move, company_currency):
        """amount_total de una factura en la moneda de la compañía. Signo negativo para notas de crédito."""
        sign = -1 if move.move_type == 'out_refund' else 1
        amt = self._convert_amount(
            move.amount_total, move.currency_id, company_currency,
            move.company_id, move.invoice_date or move.date or fields.Date.today())
        return sign * amt

    def _signed_sum(self, inv_groups, ref_groups, key, amount_field='amount_total'):
        """
        Combina dos listas de read_group (facturas y notas de crédito) por la clave dada,
        devolviendo un dict {key_value: net_amount}.
        """
        result = {}
        for g in inv_groups:
            k = g.get(key)
            if not k:
                continue
            kv = k[0] if isinstance(k, (list, tuple)) else k
            result[kv] = result.get(kv, 0.0) + (g.get(amount_field, 0.0) or 0.0)
        for g in ref_groups:
            k = g.get(key)
            if not k:
                continue
            kv = k[0] if isinstance(k, (list, tuple)) else k
            result[kv] = result.get(kv, 0.0) - (g.get(amount_field, 0.0) or 0.0)
        return result

    def _name_of(self, groups, key, value):
        """Devuelve el display_name asociado a un id en un read_group (por si no está en el otro)."""
        for g in groups:
            k = g.get(key)
            if k and (k[0] if isinstance(k, (list, tuple)) else k) == value:
                if isinstance(k, (list, tuple)) and len(k) > 1:
                    return k[1]
        return ''

    # ---------------------------------------------------------------------
    # Criterio de MERCADERÍA
    #   Mercadería = producto almacenable (bien con inventario rastreado):
    #   product.type == 'consu' AND product.is_storable == True.
    #   Las líneas de SERVICIOS, consumibles NO almacenables y líneas SIN
    #   producto NO son mercadería: se excluyen de ventas/compras/margen y se
    #   reportan aparte como "excluido" (en compras = gastos) para mostrar la
    #   nota "¿qué se excluye y por qué?" en cada gráfico.
    # ---------------------------------------------------------------------
    _MERCHANDISE_LEAVES = [
        ('product_id.type', '=', 'consu'),
        ('product_id.is_storable', '=', True),
    ]
    _NON_MERCHANDISE_LEAVES = [
        '|', '|',
        ('product_id', '=', False),
        ('product_id.type', '=', 'service'),
        ('product_id.is_storable', '=', False),
    ]

    def _period_cogs_unit(self, pids, date_from, date_to):
        """
        Costo unitario REAL (COGS) por producto, tomado de las capas de valoración
        (stock.valuation.layer) de SALIDAS A CLIENTE dentro del período. Es el
        promedio ponderado de lo efectivamente entregado: SUM(value)/SUM(quantity).

        Más fiel que standard_price (costo promedio ACTUAL) para el margen con AVCO.
        Devuelve {product_id: unit_cost (positivo)}. Los productos sin salidas
        valoradas en el período no aparecen → el caller usa standard_price de fallback.
        Respeta el conmutador de compañías (self.env.companies).
        """
        if not pids or 'stock.valuation.layer' not in self.env:
            return {}
        company_ids = self.env.companies.ids or [self.env.company.id]
        result = {}
        try:
            self.env.cr.execute('''
                SELECT svl.product_id,
                       SUM(svl.value) AS val, SUM(svl.quantity) AS qty
                FROM stock_valuation_layer svl
                JOIN stock_move sm ON sm.id = svl.stock_move_id
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dst ON dst.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND src.usage = 'internal' AND dst.usage = 'customer'
                  AND svl.company_id IN %s
                  AND svl.product_id IN %s
                  AND svl.create_date::date >= %s AND svl.create_date::date <= %s
                GROUP BY svl.product_id
            ''', (tuple(company_ids), tuple(pids), date_from, date_to))
            for row in self.env.cr.dictfetchall():
                q = float(row['qty'] or 0.0)
                v = float(row['val'] or 0.0)
                if q:
                    result[row['product_id']] = v / q  # neg/neg = positivo
        except Exception:
            return {}
        return result

    def _merchandise_exclusion(self, base_line_domain, inv_type, ref_type):
        """
        Agrega (neto factura - nota de crédito) las líneas NO-mercadería bajo el
        dominio base dado. Se usa para la nota de exclusión de los gráficos.

        Devuelve: {'amount': neto_sin_imp, 'line_count': N, 'reason': str}.
        """
        inv_dom = base_line_domain + [('move_id.move_type', '=', inv_type)] + self._NON_MERCHANDISE_LEAVES
        ref_dom = base_line_domain + [('move_id.move_type', '=', ref_type)] + self._NON_MERCHANDISE_LEAVES
        inv_g = self.env['account.move.line'].read_group(inv_dom, ['price_subtotal:sum'], [])
        ref_g = self.env['account.move.line'].read_group(ref_dom, ['price_subtotal:sum'], [])
        inv_amt = (inv_g[0].get('price_subtotal') if inv_g else 0.0) or 0.0
        ref_amt = (ref_g[0].get('price_subtotal') if ref_g else 0.0) or 0.0
        inv_cnt = (inv_g[0].get('__count') if inv_g else 0) or 0
        ref_cnt = (ref_g[0].get('__count') if ref_g else 0) or 0
        return {
            'amount': inv_amt - ref_amt,
            'line_count': inv_cnt + ref_cnt,
            'reason': ('Se excluyen líneas que no son mercadería con inventario: '
                       'servicios, productos no almacenables y líneas sin producto '
                       '(ej. fletes/despacho, impuestos, alquileres, honorarios).'),
        }

    def _received_merchandise(self, date_from, date_to):
        """
        COMPRAS DE MERCADERÍA = mercadería efectivamente RECIBIDA y valorizada
        (costo + landed costs), tomada de las capas de valoración (stock.valuation.layer)
        de entradas (dst interno) ligadas a una ORDEN DE COMPRA (purchase_line_id),
        state 'done', en el período. Respeta el selector de compañía.

        Por qué esta fuente y no las facturas: Perfipar importa y el costo real de la
        mercadería entra al inventario por recepción + landed costs, NO como líneas de
        producto en las facturas de proveedor (esas traen ~100M, irreal). El stock
        inicial de la migración NO está ligado a OC, por lo que queda excluido.

        Devuelve: total, qty, by_month {YYYY-MM: val}, by_product[], by_supplier[],
        by_category[], product_count, supplier_count.
        """
        empty = {'total': 0.0, 'qty': 0.0, 'by_month': {}, 'by_product': [],
                 'by_supplier': [], 'by_category': [], 'product_count': 0,
                 'supplier_count': 0}
        if 'stock.valuation.layer' not in self.env:
            return empty
        company_ids = self.env.companies.ids or [self.env.company.id]
        # Base común: VALOR que ingresó al stock por recepción de OC, con el criterio:
        #  - OC confirmada (state='purchase'): no cancelada, no bloqueada/locked.
        #  - solo RECEPCIÓN de proveedor (entrada), SIN devolución: se excluye toda OC
        #    que tenga alguna devolución a proveedor (interno -> proveedor).
        #  - solo MERCADERÍA (consu + almacenable), no servicios.
        #  - excluye stock inicial de migración (no está ligado a OC).
        base = '''
            FROM stock_valuation_layer svl
            JOIN stock_move sm ON sm.id = svl.stock_move_id
            JOIN stock_location src ON src.id = sm.location_id
            JOIN stock_location dst ON dst.id = sm.location_dest_id
            JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
            JOIN purchase_order po ON po.id = pol.order_id
            JOIN product_product pp ON pp.id = svl.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE sm.state = 'done'
              AND src.usage = 'supplier' AND dst.usage = 'internal'
              AND po.state = 'purchase'
              AND pt.type = 'consu' AND pt.is_storable = TRUE
              AND svl.company_id IN %(cids)s
              AND svl.create_date::date >= %(df)s AND svl.create_date::date <= %(dt)s
              AND po.id NOT IN (
                  SELECT DISTINCT pol2.order_id FROM stock_move sm2
                  JOIN stock_location s2 ON s2.id = sm2.location_id
                  JOIN stock_location d2 ON d2.id = sm2.location_dest_id
                  JOIN purchase_order_line pol2 ON pol2.id = sm2.purchase_line_id
                  WHERE sm2.state = 'done' AND s2.usage = 'internal' AND d2.usage = 'supplier')
        '''
        p = {'cids': tuple(company_ids), 'df': date_from, 'dt': date_to}
        try:
            self.env.cr.execute('SELECT COALESCE(SUM(svl.value),0) v, COALESCE(SUM(svl.quantity),0) q ' + base, p)
            row = self.env.cr.dictfetchone()
            total = float(row['v'] or 0.0); qty = float(row['q'] or 0.0)
            self.env.cr.execute("SELECT to_char(svl.create_date,'YYYY-MM') m, SUM(svl.value) v " + base + ' GROUP BY 1', p)
            by_month = {r['m']: float(r['v'] or 0.0) for r in self.env.cr.dictfetchall()}
            self.env.cr.execute('SELECT svl.product_id pid, SUM(svl.value) v, SUM(svl.quantity) q '
                                + base + ' GROUP BY svl.product_id ORDER BY v DESC LIMIT 20', p)
            prod_rows = self.env.cr.dictfetchall()
            self.env.cr.execute('SELECT COUNT(DISTINCT svl.product_id) n ' + base, p)
            product_count = self.env.cr.dictfetchone()['n'] or 0
            self.env.cr.execute('SELECT po.partner_id pid, SUM(svl.value) v '
                                + base + ' GROUP BY po.partner_id ORDER BY v DESC', p)
            sup_rows = self.env.cr.dictfetchall()
            self.env.cr.execute('SELECT pt.categ_id cid, SUM(svl.value) v, SUM(svl.quantity) q, '
                                'COUNT(DISTINCT svl.product_id) n ' + base + ' GROUP BY pt.categ_id', p)
            cat_rows = self.env.cr.dictfetchall()
        except Exception:
            return empty

        # Nombres de productos / proveedores / categorías
        prod_ids = [r['pid'] for r in prod_rows if r['pid']]
        prods = {p2.id: p2 for p2 in self.env['product.product'].browse(prod_ids)}
        by_product = []
        for r in prod_rows:
            pr = prods.get(r['pid'])
            by_product.append({
                'id': r['pid'],
                'name': (pr.name if pr else '') or '',
                'code': (pr.default_code if pr else '') or '',
                'category': (pr.categ_id.name if (pr and pr.categ_id) else ''),
                'amount': float(r['v'] or 0.0),
                'qty': float(r['q'] or 0.0),
            })
        part_ids = [r['pid'] for r in sup_rows if r['pid']]
        parts = {pp2.id: pp2 for pp2 in self.env['res.partner'].browse(part_ids)}
        by_supplier = [{'id': r['pid'], 'name': (parts.get(r['pid']).name if parts.get(r['pid']) else '') or '',
                        'amount': float(r['v'] or 0.0)} for r in sup_rows[:10]]
        cat_ids = [r['cid'] for r in cat_rows if r['cid']]
        cats = {c.id: c for c in self.env['product.category'].browse(cat_ids)}
        by_category = sorted([{
            'category_id': r['cid'] or 0,
            'name': (cats.get(r['cid']).name if cats.get(r['cid']) else 'Sin Categoría'),
            'amount': float(r['v'] or 0.0),
            'qty': float(r['q'] or 0.0),
            'product_count': r['n'] or 0,
        } for r in cat_rows], key=lambda c: c['amount'], reverse=True)

        return {
            'total': total, 'qty': qty, 'by_month': by_month,
            'by_product': by_product, 'by_supplier': by_supplier,
            'by_category': by_category, 'product_count': product_count,
            'supplier_count': len(part_ids),
        }

    # ---------------------------------------------------------------------
    # Endpoint principal
    # ---------------------------------------------------------------------
    @api.model
    def get_commercial_data(self, filters=None):
        if filters is None:
            filters = {}

        # INC-02: selector de compañía (Matriz / Asunción / Consolidado).
        # Acota allowed_company_ids para que TODO el método (ORM) consolide o filtre.
        company_options = self._company_options()
        selected_company_ids = sorted(self._effective_company_ids(filters))
        self = self.with_context(allowed_company_ids=selected_company_ids)

        today = fields.Date.today()
        first_day_month = today.replace(day=1)
        date_from = self._as_date(filters.get('date_from'), first_day_month)
        date_to = self._as_date(filters.get('date_to'), today)
        dt_from = self._day_start(date_from)
        dt_to = self._day_end(date_to)

        company_currency = self.env.company.currency_id

        partner_id = int(filters['partner_id']) if filters.get('partner_id') else None
        product_id = int(filters['product_id']) if filters.get('product_id') else None
        category_id = int(filters['category_id']) if filters.get('category_id') else None

        # Dominio base de facturas posteadas (out_invoice + out_refund) en el período.
        # invoice_date es un Date (no Datetime), así que comparamos con date_from/date_to planos.
        base_move_domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('company_id', 'in', selected_company_ids),  # INC-02: filtro explícito de compañía
        ]
        if partner_id:
            base_move_domain.append(('partner_id', '=', partner_id))
        if product_id:
            base_move_domain.append(('invoice_line_ids.product_id', '=', product_id))
        if category_id:
            base_move_domain.append(('invoice_line_ids.product_id.categ_id', '=', category_id))

        inv_domain = base_move_domain + [('move_type', '=', 'out_invoice')]
        ref_domain = base_move_domain + [('move_type', '=', 'out_refund')]

        # Dominio base de líneas (para análisis de producto/categoría/margen)
        base_line_domain = [
            ('parent_state', '=', 'posted'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to),
            ('display_type', '=', 'product'),
            ('company_id', 'in', selected_company_ids),  # INC-02: filtro explícito de compañía
        ]
        if partner_id:
            base_line_domain.append(('move_id.partner_id', '=', partner_id))
        if product_id:
            base_line_domain.append(('product_id', '=', product_id))
        if category_id:
            base_line_domain.append(('product_id.categ_id', '=', category_id))

        inv_line_domain = base_line_domain + [('move_id.move_type', '=', 'out_invoice')]
        ref_line_domain = base_line_domain + [('move_id.move_type', '=', 'out_refund')]

        # =============== 1. KPIs Generales (IVA incluido, netos de NC) ===============
        moves = self.env['account.move'].search(base_move_domain)

        total_sales = sum(self._move_amount_in_company(m, company_currency) for m in moves)
        sale_count = len([m for m in moves if m.move_type == 'out_invoice'])
        avg_ticket = (total_sales / sale_count) if sale_count else 0.0

        # INC-01: Ganancia Bruta unificada al MISMO criterio que el tablero Productos:
        # ingreso NETO (sin IVA, neto de NC) menos COSTO REAL (capas de valoración /
        # COGS), en vez de standard_price. Una sola definición de utilidad bruta.
        inv_pg = self.env['account.move.line'].read_group(
            inv_line_domain, ['product_id', 'price_subtotal:sum', 'quantity:sum'], ['product_id'])
        ref_pg = self.env['account.move.line'].read_group(
            ref_line_domain, ['product_id', 'price_subtotal:sum', 'quantity:sum'], ['product_id'])
        net_rev_by_prod = self._signed_sum(inv_pg, ref_pg, 'product_id', 'price_subtotal')
        qty_by_prod = self._signed_sum(inv_pg, ref_pg, 'product_id', 'quantity')
        net_revenue = sum(net_rev_by_prod.values())
        cogs_pids = list(qty_by_prod.keys())
        cogs_unit = self._period_cogs_unit(cogs_pids, date_from, date_to)
        cost_prods = {p.id: p for p in self.env['product.product'].browse(cogs_pids)}
        total_period_cost = 0.0
        for pid, q in qty_by_prod.items():
            u = cogs_unit.get(pid)
            if u is None:
                pr = cost_prods.get(pid)
                u = (pr.standard_price or 0.0) if pr else 0.0
            total_period_cost += u * q
        total_profit = net_revenue - total_period_cost
        gross_margin_pct = (total_profit / net_revenue * 100.0) if net_revenue > 0 else 0.0

        # "En Negociación" = sale.order que aún están "en juego":
        #   - Presupuestos (state in draft/sent), o
        #   - Ventas confirmadas (state in sale/done) que NO tienen factura asociada.
        # Se respetan filtros de fecha, cliente, producto y categoría.
        quo_domain = [
            '|',
                ('state', 'in', ['draft', 'sent']),
                '&', ('state', 'in', ['sale', 'done']),
                     ('invoice_ids', '=', False),
            ('date_order', '>=', dt_from),
            ('date_order', '<=', dt_to),
            ('company_id', 'in', selected_company_ids),  # INC-02
        ]
        if partner_id:
            quo_domain.append(('partner_id', '=', partner_id))
        if product_id:
            quo_domain.append(('order_line.product_id', '=', product_id))
        if category_id:
            quo_domain.append(('order_line.product_id.categ_id', '=', category_id))
        quotations = self.env['sale.order'].search(quo_domain)
        open_pipe = 0.0
        for q in quotations:
            amt = self._convert_amount(q.amount_total, q.currency_id, company_currency,
                                       q.company_id, q.date_order or fields.Date.today())
            open_pipe += amt
        opp_count = len(quotations)

        # Conversión CRM (no cambia)
        conv_base = [('type', '=', 'opportunity'), ('company_id', 'in', selected_company_ids)]
        if partner_id:
            conv_base.append(('partner_id', '=', partner_id))
        won_opps = self.env['crm.lead'].search_count(conv_base + [
            ('probability', '=', 100), ('active', '=', True),
            ('date_closed', '>=', dt_from), ('date_closed', '<=', dt_to)])
        lost_opps = self.env['crm.lead'].search_count(conv_base + [
            ('probability', '=', 0), ('active', '=', False),
            ('date_closed', '>=', dt_from), ('date_closed', '<=', dt_to)])
        total_closed = won_opps + lost_opps
        conversion_rate = (won_opps / total_closed * 100) if total_closed else 0.0
        conversion_basis = 'crm'
        # INC-03: si no hay oportunidades CRM cerradas (Perfipar no usa CRM), el ratio
        # CRM siempre da 0. Fallback comercial: pedidos confirmados / presupuestos
        # emitidos en el período (sale.order), que sí es medible.
        if total_closed == 0:
            so_dom = [('date_order', '>=', dt_from), ('date_order', '<=', dt_to),
                      ('company_id', 'in', selected_company_ids)]
            if partner_id:
                so_dom.append(('partner_id', '=', partner_id))
            total_quotes = self.env['sale.order'].search_count(so_dom)
            confirmed_quotes = self.env['sale.order'].search_count(
                so_dom + [('state', 'in', ['sale', 'done'])])
            if total_quotes:
                conversion_rate = confirmed_quotes / total_quotes * 100.0
                conversion_basis = 'sale_order'

        # =============== 2. Pipeline Funnel (CRM) ===============
        crm_domain = [('type', '=', 'opportunity'), ('active', '=', True),
                      ('company_id', 'in', selected_company_ids)]
        if partner_id:
            crm_domain.append(('partner_id', '=', partner_id))
        stages = self.env['crm.stage'].search([])
        stage_groups = self.env['crm.lead'].read_group(
            crm_domain, ['stage_id', 'expected_revenue:sum'], ['stage_id'])
        stage_map = {g['stage_id'][0]: g for g in stage_groups if g.get('stage_id')}
        funnel_data = [{
            'name': stage.name,
            'count': stage_map.get(stage.id, {}).get('__count', 0),
            'revenue': stage_map.get(stage.id, {}).get('expected_revenue', 0.0),
        } for stage in stages]

        # =============== 3. Top Vendedores (invoice_user_id) ===============
        inv_user_g = self.env['account.move'].read_group(
            inv_domain, ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        ref_user_g = self.env['account.move'].read_group(
            ref_domain, ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        user_net = self._signed_sum(inv_user_g, ref_user_g, 'invoice_user_id')
        top_salespeople = []
        for uid, amt in sorted(user_net.items(), key=lambda x: x[1], reverse=True)[:5]:
            name = self._name_of(inv_user_g, 'invoice_user_id', uid) \
                or self._name_of(ref_user_g, 'invoice_user_id', uid) \
                or self.env['res.users'].browse(uid).name
            top_salespeople.append({'id': uid, 'name': name or '', 'amount': amt})

        # =============== 4. Salud del Cliente (respeta filtros) ===============
        days_lost = int(self.env['ir.config_parameter'].sudo().get_param(
            'dashboard_cross.lost_customer_days', 90))
        lost_date_threshold = today - datetime.timedelta(days=days_lost)
        period_partner_ids = list({m.partner_id.id for m in moves if m.partner_id})

        new_customers = recurring_customers = lost_customers = 0
        total_lifetime = 0.0
        avg_lifetime_value = 0.0

        if period_partner_ids:
            new_customers = self.env['res.partner'].search_count([
                ('id', 'in', period_partner_ids),
                ('create_date', '>=', dt_from),
                ('create_date', '<=', dt_to)])
            self.env.cr.execute('''
                SELECT partner_id,
                       COUNT(id) AS ord_cnt,
                       MAX(invoice_date) AS last_invoice,
                       SUM(CASE WHEN move_type='out_refund' THEN -amount_total ELSE amount_total END) AS tot_rev
                FROM account_move
                WHERE state = 'posted'
                  AND move_type IN ('out_invoice','out_refund')
                  AND partner_id IN %s
                GROUP BY partner_id
            ''', (tuple(period_partner_ids),))
            customer_rows = self.env.cr.dictfetchall()
            for row in customer_rows:
                if row['ord_cnt'] > 1:
                    recurring_customers += 1
                last_dt = row['last_invoice']
                if isinstance(last_dt, str):
                    last_dt = fields.Date.from_string(last_dt)
                if last_dt and last_dt < lost_date_threshold:
                    lost_customers += 1
                total_lifetime += (row['tot_rev'] or 0.0)
            avg_lifetime_value = (total_lifetime / len(customer_rows)) if customer_rows else 0.0

        customer_health = {
            'new': new_customers, 'recurring': recurring_customers,
            'lost': lost_customers, 'avg_lifetime_value': avg_lifetime_value,
        }

        # =============== 5. Product Portfolio (facturas) ===============
        inv_prod_g = self.env['account.move.line'].read_group(
            inv_line_domain,
            ['product_id', 'price_total:sum', 'quantity:sum'],
            ['product_id'])
        ref_prod_g = self.env['account.move.line'].read_group(
            ref_line_domain,
            ['product_id', 'price_total:sum', 'quantity:sum'],
            ['product_id'])
        # Net por producto
        prod_rev = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', 'price_total')
        prod_qty = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', 'quantity')

        all_pids = list(set(list(prod_rev.keys()) + list(prod_qty.keys())))
        prods = self.env['product.product'].browse(all_pids)
        if prods:
            prods.read(['standard_price', 'type', 'qty_available', 'categ_id', 'name', 'default_code'])
        prod_info = {p.id: p for p in prods}

        # Última fecha de factura por producto (para days_in_stock)
        last_sale_map = {}
        if all_pids:
            self.env.cr.execute('''
                SELECT aml.product_id, MAX(am.invoice_date) AS last_sold
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE am.state = 'posted'
                  AND am.move_type = 'out_invoice'
                  AND aml.product_id IN %s
                GROUP BY aml.product_id
            ''', (tuple(all_pids),))
            for row in self.env.cr.dictfetchall():
                last_dt = row['last_sold']
                if isinstance(last_dt, str):
                    last_dt = fields.Date.from_string(last_dt)
                if last_dt:
                    last_sale_map[row['product_id']] = last_dt

        product_performance = []
        for pid, revenue in prod_rev.items():
            qty = prod_qty.get(pid, 0.0)
            product = prod_info.get(pid)
            if not product:
                continue
            cost = product.standard_price * qty
            margin = ((revenue - cost) / revenue * 100) if revenue > 0 else 0.0
            days_no_rotation = 0
            if (product.type or '') in ('product', 'consu') and (product.qty_available or 0) > 0:
                last_sold = last_sale_map.get(pid)
                if last_sold:
                    days_no_rotation = max((today - last_sold).days, 0)
                else:
                    days_no_rotation = 999
            product_performance.append({
                'id': pid,
                'name': product.name or '',          # sólo el nombre, sin [CODIGO]
                'code': product.default_code or '',  # código como campo aparte
                'revenue': revenue, 'margin': margin,
                'days_in_stock': days_no_rotation,
            })

        product_performance.sort(key=lambda x: x['revenue'], reverse=True)
        top_sellers = product_performance[:5]
        high_margin = sorted([p for p in product_performance if p['margin'] > 0],
                             key=lambda x: x['margin'], reverse=True)[:5]
        low_rotation = sorted([p for p in product_performance if p['days_in_stock'] > 0],
                              key=lambda x: x['days_in_stock'], reverse=True)[:5]
        product_portfolio = {
            'top_sellers': top_sellers, 'high_margin': high_margin, 'low_rotation': low_rotation,
        }

        # =============== 6. Top 10 Clientes ===============
        inv_part_g = self.env['account.move'].read_group(
            inv_domain, ['partner_id', 'amount_total:sum'], ['partner_id'])
        ref_part_g = self.env['account.move'].read_group(
            ref_domain, ['partner_id', 'amount_total:sum'], ['partner_id'])
        part_net = self._signed_sum(inv_part_g, ref_part_g, 'partner_id')
        top_customers = []
        for pid, amt in sorted(part_net.items(), key=lambda x: x[1], reverse=True)[:10]:
            name = self._name_of(inv_part_g, 'partner_id', pid) \
                or self._name_of(ref_part_g, 'partner_id', pid) \
                or self.env['res.partner'].browse(pid).name
            top_customers.append({'id': pid, 'name': name or '', 'amount': amt})

        # =============== 7. Tendencia y Métodos de Pago (dinámico según rango) ===============
        # Se generan exactamente los buckets mensuales que abarca el rango filtrado
        # (date_from..date_to), sin relleno. Los labels incluyen el año cuando cubren
        # más de 12 meses o cuando cruzan años calendario distintos.
        trends_current, trend_cash, trend_credit = [], [], []
        trend_cost, trend_profit = [], []
        months_labels = []
        months_ranges = []  # [{'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}] para drill-down

        bucket_first = date_from.replace(day=1)
        bucket_last_start = date_to.replace(day=1)
        months_span = ((bucket_last_start.year - bucket_first.year) * 12
                       + (bucket_last_start.month - bucket_first.month) + 1)
        # Se muestran exactamente los meses del rango filtrado (sin relleno).

        # Etiqueta con año si cubrimos más de 12 meses o cruzamos calendarios
        use_year_suffix = months_span > 12 or bucket_first.year != bucket_last_start.year
        label_fmt = '%b/%y' if use_year_suffix else '%b'

        # Iterar meses de bucket_first a bucket_last_start inclusive
        buckets = []
        cursor = bucket_first
        while cursor <= bucket_last_start:
            bucket_end = cursor + relativedelta(months=1, days=-1)
            buckets.append((cursor, bucket_end))
            cursor = cursor + relativedelta(months=1)

        for start, end in buckets:

            m_base = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', start),
                ('invoice_date', '<=', end),
            ]
            if partner_id:
                m_base.append(('partner_id', '=', partner_id))
            if product_id:
                m_base.append(('invoice_line_ids.product_id', '=', product_id))
            if category_id:
                m_base.append(('invoice_line_ids.product_id.categ_id', '=', category_id))

            inv_pay_g = self.env['account.move'].read_group(
                m_base + [('move_type', '=', 'out_invoice')],
                ['amount_total:sum'], ['invoice_payment_term_id'])
            ref_pay_g = self.env['account.move'].read_group(
                m_base + [('move_type', '=', 'out_refund')],
                ['amount_total:sum'], ['invoice_payment_term_id'])

            month_total = m_cash = m_credit = 0.0
            def classify(groups, sign):
                nonlocal month_total, m_cash, m_credit
                for g in groups:
                    amt = (g.get('amount_total', 0.0) or 0.0) * sign
                    month_total += amt
                    term = g.get('invoice_payment_term_id')
                    term_name = ''
                    if term:
                        term_name = (term[1] or '').lower() if isinstance(term, (list, tuple)) else ''
                    if not term or 'inmediato' in term_name or 'contado' in term_name:
                        m_cash += amt
                    else:
                        m_credit += amt
            classify(inv_pay_g, 1)
            classify(ref_pay_g, -1)

            # Costo mensual (líneas)
            line_m_inv = [
                ('parent_state', '=', 'posted'),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.invoice_date', '>=', start),
                ('move_id.invoice_date', '<=', end),
                ('display_type', '=', 'product'),
            ]
            line_m_ref = list(line_m_inv)
            line_m_ref[1] = ('move_id.move_type', '=', 'out_refund')
            for ld in (line_m_inv, line_m_ref):
                if partner_id:
                    ld.append(('move_id.partner_id', '=', partner_id))
                if product_id:
                    ld.append(('product_id', '=', product_id))
                if category_id:
                    ld.append(('product_id.categ_id', '=', category_id))

            lines_inv = self.env['account.move.line'].search(line_m_inv)
            lines_ref = self.env['account.move.line'].search(line_m_ref)
            if lines_inv:
                lines_inv.mapped('product_id').read(['standard_price'])
            if lines_ref:
                lines_ref.mapped('product_id').read(['standard_price'])
            total_month_cost = 0.0
            for line in lines_inv:
                if line.product_id:
                    total_month_cost += line.product_id.standard_price * (line.quantity or 0.0)
            for line in lines_ref:
                if line.product_id:
                    total_month_cost -= line.product_id.standard_price * (line.quantity or 0.0)
            month_profit = month_total - total_month_cost

            trends_current.append(month_total)
            trend_cash.append(m_cash)
            trend_credit.append(m_credit)
            trend_cost.append(total_month_cost)
            trend_profit.append(month_profit)
            months_labels.append(start.strftime(label_fmt))
            months_ranges.append({'start': start.isoformat(), 'end': end.isoformat()})

        # =============== 8. Análisis por Vendedor ===============
        salesperson_analysis = {
            'labels': [], 'cash': [], 'credit': [],
            'cash_qty': [], 'credit_qty': [],
            'new_cust': [], 'recurring_cust': [],
            'new_cust_qty': [], 'recurring_cust_qty': [],
            'margins': [], 'distribution': [], 'distribution_qty': [],
        }
        # Lista ordenada de vendedores por venta neta
        sorted_users = sorted(user_net.items(), key=lambda x: x[1], reverse=True)

        new_from = dt_from
        new_to = dt_to

        for uid, _net in sorted_users:
            if not uid:
                continue
            uname = self._name_of(inv_user_g, 'invoice_user_id', uid) \
                or self._name_of(ref_user_g, 'invoice_user_id', uid) \
                or self.env['res.users'].browse(uid).name

            user_moves = self.env['account.move'].search(base_move_domain + [('invoice_user_id', '=', uid)])
            s_cash = s_credit = 0.0
            s_cash_qty = s_credit_qty = 0.0
            s_new = s_recur = 0.0
            s_new_qty = s_recur_qty = 0.0

            partners = user_moves.mapped('partner_id')
            if partners:
                partners.read(['create_date'])
            p_create = {p.id: p.create_date for p in partners}

            # Cantidades totales por move_id
            user_line_qg = self.env['account.move.line'].read_group(
                [('move_id', 'in', user_moves.ids), ('display_type', '=', 'product')],
                ['quantity:sum'], ['move_id'])
            qty_map = {g['move_id'][0]: (g.get('quantity', 0.0) or 0.0) for g in user_line_qg}

            for m in user_moves:
                sign = -1 if m.move_type == 'out_refund' else 1
                amt = sign * self._convert_amount(
                    m.amount_total, m.currency_id, company_currency,
                    m.company_id, m.invoice_date or fields.Date.today())
                qty = sign * qty_map.get(m.id, 0.0)

                term = m.invoice_payment_term_id
                term_name = (term.name or '').lower() if term else ''
                is_cash = (not term) or 'inmediato' in term_name or 'contado' in term_name
                if is_cash:
                    s_cash += amt
                    s_cash_qty += qty
                else:
                    s_credit += amt
                    s_credit_qty += qty

                if m.partner_id:
                    c_date = p_create.get(m.partner_id.id)
                    if c_date and new_from <= c_date <= new_to:
                        s_new += amt
                        s_new_qty += qty
                    else:
                        s_recur += amt
                        s_recur_qty += qty

            # Margen
            user_lines = self.env['account.move.line'].search(
                base_line_domain + [('move_id.invoice_user_id', '=', uid)])
            if user_lines:
                user_lines.mapped('product_id').read(['standard_price'])
            s_revenue = s_cost = 0.0
            for line in user_lines:
                if not line.product_id:
                    continue
                sign = -1 if line.move_id.move_type == 'out_refund' else 1
                s_revenue += sign * (line.price_total or 0.0)
                s_cost += sign * line.product_id.standard_price * (line.quantity or 0.0)
            s_margin = ((s_revenue - s_cost) / s_revenue * 100) if s_revenue > 0 else 0.0

            salesperson_analysis['labels'].append(uname)
            salesperson_analysis['cash'].append(s_cash)
            salesperson_analysis['credit'].append(s_credit)
            salesperson_analysis['cash_qty'].append(s_cash_qty)
            salesperson_analysis['credit_qty'].append(s_credit_qty)
            salesperson_analysis['new_cust'].append(s_new)
            salesperson_analysis['recurring_cust'].append(s_recur)
            salesperson_analysis['new_cust_qty'].append(s_new_qty)
            salesperson_analysis['recurring_cust_qty'].append(s_recur_qty)
            salesperson_analysis['margins'].append(s_margin)
            salesperson_analysis['distribution'].append(s_revenue)
            salesperson_analysis['distribution_qty'].append(s_cash_qty + s_credit_qty)

        # =============== 9. Análisis de Categorías ===============
        category_analysis = {
            'labels': [], 'revenue': [], 'revenue_qty': [],
            'margins': [], 'rotation': [],
        }
        cat_map = {}
        for pid, revenue in prod_rev.items():
            qty = prod_qty.get(pid, 0.0)
            product = prod_info.get(pid)
            if not product:
                continue
            categ = product.categ_id
            cid = categ.id
            if cid not in cat_map:
                cat_map[cid] = {'name': categ.name or 'Sin Categoría',
                                'revenue': 0.0, 'cost': 0.0, 'qty': 0.0}
            cat_map[cid]['revenue'] += revenue
            cat_map[cid]['cost'] += product.standard_price * qty
            cat_map[cid]['qty'] += qty

        for cdict in sorted(cat_map.values(), key=lambda x: x['revenue'], reverse=True):
            rev = cdict['revenue']
            margin = ((rev - cdict['cost']) / rev * 100) if rev > 0 else 0.0
            category_analysis['labels'].append(cdict['name'])
            category_analysis['revenue'].append(rev)
            category_analysis['revenue_qty'].append(cdict['qty'])
            category_analysis['margins'].append(margin)
            category_analysis['rotation'].append(cdict['qty'])

        # =============== Currency info ===============
        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }

        return {
            'currency': currency_info,
            'company': self._company_branding(),
            'companies': company_options,
            'selected_company_ids': selected_company_ids,
            'taxes_included': True,
            'data_source': 'account.move',
            'kpis': {
                'total_sales': total_sales,
                'total_profit': total_profit,
                # Ingreso neto (sin IVA) y margen %, base del profit unificado (INC-01).
                'net_revenue': net_revenue,
                'gross_margin_pct': gross_margin_pct,
                'avg_ticket': avg_ticket,
                'open_pipe': open_pipe,
                'opp_count': opp_count,
                'conversion_rate': conversion_rate,
                'conversion_basis': conversion_basis,
            },
            'funnel': funnel_data,
            'top_salespeople': top_salespeople,
            'top_customers': top_customers,
            'customer_health': customer_health,
            'product_portfolio': product_portfolio,
            'payment_methods': {
                'labels': months_labels, 'cash': trend_cash, 'credit': trend_credit,
            },
            'months_ranges': months_ranges,
            'trends': {
                'labels': months_labels,
                'current_year': trends_current,
                'last_year': [0] * len(trends_current),
            },
            'revenue_composition': {
                'labels': months_labels,
                'revenue': trends_current,
                'cost': trend_cost,
                'profit': trend_profit,
            },
            'salesperson_analysis': salesperson_analysis,
            'category_analysis': category_analysis,
        }

    # =====================================================================
    # Endpoint Dashboard de PRODUCTOS (vista dedicada)
    # =====================================================================
    def _resolve_period_preset(self, preset, today):
        """
        Convierte un preset ('3m', '6m', '9m', '12m', '12m_compare') en
        (date_from, date_to). Si el preset no aplica, retorna (None, None).
        '12m_compare' devuelve el mismo rango que '12m' (la comparacion la
        gestiona aparte el endpoint).
        """
        months_map = {
            '3m': 3, '6m': 6, '9m': 9, '12m': 12, '12m_compare': 12,
        }
        n = months_map.get((preset or '').lower())
        if not n:
            return None, None
        end_of_month = today.replace(day=1) + relativedelta(months=1, days=-1)
        start = today.replace(day=1) - relativedelta(months=n - 1)
        return start, end_of_month

    @api.model
    def get_product_dashboard_data(self, filters=None):
        """
        Datos para el dashboard "Productos":
          * Desglose mensual de ventas: barras apiladas con los Top 8 productos
            (o categorias) del período + segmento "Otros".
          * Ranking de productos (con monto, cantidad y antigüedad en días
            desde la primera recepción de stock - fallback create_date).

        Filtros aceptados:
          - preset ('3m'|'6m'|'9m'|'12m'|'12m_compare'): si esta, define el
            rango automaticamente y sobreescribe date_from/date_to.
          - date_from / date_to (rango del período, usados si preset no esta)
          - category_id (filtra por categoría de producto)
          - product_ids (lista opcional para acotar el universo a estos productos)
          - antiquity (cadena: 'all', 'lt90', '90_365', 'gt365')
          - group_by ('product' [default] | 'category'): cómo apilar las barras
        """
        if filters is None:
            filters = {}

        # Selector de compañía: acota el contexto a las compañías efectivas para que
        # TODO (consultas ORM y SQL crudo) quede consistente. Vacío/ambas = suma todo.
        company_options = self._company_options()
        selected_company_ids = self._effective_company_ids(filters)
        # env.company = primer elemento de allowed_company_ids en Odoo 18, así que
        # ordenamos ascendente: la compañía de referencia para el costo único es la
        # de menor id (MATRIZ cuando están ambas). Determinístico sin importar la sesión.
        selected_company_ids = sorted(selected_company_ids)
        self = self.with_context(allowed_company_ids=selected_company_ids)

        today = fields.Date.today()

        # Si viene preset, sobreescribe date_from/date_to
        preset = (filters.get('preset') or '').lower()
        p_from, p_to = self._resolve_period_preset(preset, today)
        if p_from and p_to:
            date_from = p_from
            date_to = p_to
        else:
            # Default: últimos 6 meses
            default_to = today.replace(day=1) + relativedelta(months=1, days=-1)
            default_from = (today.replace(day=1) - relativedelta(months=5))
            date_from = self._as_date(filters.get('date_from'), default_from)
            date_to = self._as_date(filters.get('date_to'), default_to)

        category_id = int(filters['category_id']) if filters.get('category_id') else None
        product_ids = filters.get('product_ids') or []
        try:
            product_ids = [int(x) for x in product_ids if x]
        except Exception:
            product_ids = []

        antiquity_bucket = (filters.get('antiquity') or 'all').lower()
        group_by = (filters.get('group_by') or 'product').lower()
        if group_by not in ('product', 'category'):
            group_by = 'product'

        # Top N configurable (default 8)
        try:
            top_n = int(filters.get('top_n') or 8)
        except Exception:
            top_n = 8
        if top_n not in (8, 15, 25):
            top_n = 8

        company_currency = self.env.company.currency_id

        # Dominio base de líneas en el período
        base_line_domain = [
            ('parent_state', '=', 'posted'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to),
            ('display_type', '=', 'product'),
        ]
        if category_id:
            base_line_domain.append(('product_id.categ_id', '=', category_id))
        if product_ids:
            base_line_domain.append(('product_id', 'in', product_ids))

        # Nota de exclusión: facturación NO-mercadería (servicios, no almacenables,
        # sin producto) que queda fuera ANTES de aplicar el filtro de mercadería.
        merchandise_filter = self._merchandise_exclusion(
            base_line_domain, 'out_invoice', 'out_refund')
        # A partir de acá, todo el dashboard de ventas considera solo mercadería.
        base_line_domain = base_line_domain + self._MERCHANDISE_LEAVES

        inv_line_dom = base_line_domain + [('move_id.move_type', '=', 'out_invoice')]
        ref_line_dom = base_line_domain + [('move_id.move_type', '=', 'out_refund')]

        # ------------------------------------------------
        # Totales del período por producto (para determinar Top 8 + Otros)
        # ------------------------------------------------
        # Check "Impuesto incluido": elige el campo de facturación a mostrar.
        # Default neto (sin IVA). El MARGEN siempre usa neto (el costo no lleva IVA).
        rev_field = 'price_total' if filters.get('tax_included') else 'price_subtotal'
        inv_prod_g = self.env['account.move.line'].read_group(
            inv_line_dom,
            ['product_id', 'price_total:sum', 'price_subtotal:sum', 'quantity:sum'],
            ['product_id'])
        ref_prod_g = self.env['account.move.line'].read_group(
            ref_line_dom,
            ['product_id', 'price_total:sum', 'price_subtotal:sum', 'quantity:sum'],
            ['product_id'])

        prod_rev = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', rev_field)
        prod_rev_net = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', 'price_subtotal')
        prod_qty = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', 'quantity')

        all_pids = list(set(list(prod_rev.keys()) + list(prod_qty.keys())))

        # ------------------------------------------------
        # Antigüedad por producto (primera recepción / create_date)
        # + última recepción DENTRO del período (para clasificar origen del stock vendido)
        # ------------------------------------------------
        first_reception_map = {}            # TODAS las recepciones (para antigüedad)
        last_reception_in_period_map = {}
        first_po_reception_map = {}         # solo COMPRAS REALES ligadas a OC (para origen)
        last_po_reception_in_period_map = {}
        if all_pids and 'stock.move' in self.env:
            try:
                self.env.cr.execute('''
                    SELECT sm.product_id,
                           MIN(sm.date)::date AS first_recv,
                           MAX(CASE WHEN sm.date::date >= %s AND sm.date::date <= %s
                                    THEN sm.date::date END) AS last_recv_in_period,
                           MIN(CASE WHEN sm.purchase_line_id IS NOT NULL
                                    THEN sm.date::date END) AS first_recv_po,
                           MAX(CASE WHEN sm.purchase_line_id IS NOT NULL
                                     AND sm.date::date >= %s AND sm.date::date <= %s
                                    THEN sm.date::date END) AS last_recv_po_in_period
                    FROM stock_move sm
                    JOIN stock_location sl ON sl.id = sm.location_id
                    WHERE sm.state = 'done'
                      AND sl.usage = 'supplier'
                      AND sm.product_id IN %s
                    GROUP BY sm.product_id
                ''', (date_from, date_to, date_from, date_to, tuple(all_pids),))
                for row in self.env.cr.dictfetchall():
                    def _d(v):
                        return fields.Date.from_string(v) if isinstance(v, str) else v
                    fr = _d(row['first_recv'])
                    if fr:
                        first_reception_map[row['product_id']] = fr
                    lrp = _d(row['last_recv_in_period'])
                    if lrp:
                        last_reception_in_period_map[row['product_id']] = lrp
                    frpo = _d(row['first_recv_po'])
                    if frpo:
                        first_po_reception_map[row['product_id']] = frpo
                    lppo = _d(row['last_recv_po_in_period'])
                    if lppo:
                        last_po_reception_in_period_map[row['product_id']] = lppo
            except Exception:
                first_reception_map = {}
                last_reception_in_period_map = {}
                first_po_reception_map = {}
                last_po_reception_in_period_map = {}

        prods = self.env['product.product'].browse(all_pids)
        if prods:
            prods.read(['name', 'default_code', 'create_date', 'categ_id', 'standard_price'])
        prod_info = {p.id: p for p in prods}

        def _antiquity(pid):
            product = prod_info.get(pid)
            fr = first_reception_map.get(pid)
            if fr:
                return max((today - fr).days, 0), 'reception'
            if product and product.create_date:
                cd = product.create_date
                if isinstance(cd, datetime.datetime):
                    cd = cd.date()
                return max((today - cd).days, 0), 'created'
            return 0, 'unknown'

        # Aplicar filtro de antigüedad sobre el universo de productos
        def in_bucket(days):
            if antiquity_bucket == 'lt90':
                return days < 90
            if antiquity_bucket == '90_365':
                return 90 <= days < 365
            if antiquity_bucket == 'gt365':
                return days >= 365
            return True

        filtered_pids = []
        antiquity_map = {}
        for pid in all_pids:
            d, src = _antiquity(pid)
            antiquity_map[pid] = {'days': d, 'source': src}
            if in_bucket(d):
                filtered_pids.append(pid)

        # ------------------------------------------------
        # Ranking de productos (filtrados) ordenado por revenue
        # ------------------------------------------------
        # Costo unitario REAL (COGS) de las salidas del período (SVL). Fallback a
        # standard_price para productos sin salidas valoradas en el período.
        cogs_unit_map = self._period_cogs_unit(filtered_pids, date_from, date_to)
        ranking = []
        for pid in filtered_pids:
            product = prod_info.get(pid)
            if not product:
                continue
            revenue = prod_rev.get(pid, 0.0)            # facturación a mostrar (con/sin IVA)
            revenue_net = prod_rev_net.get(pid, 0.0)    # neto, para el margen
            qty = prod_qty.get(pid, 0.0)
            unit_cost = cogs_unit_map.get(pid)
            if unit_cost is None:
                unit_cost = product.standard_price or 0.0
            cost = unit_cost * qty
            margin = revenue_net - cost
            margin_pct = (margin / revenue_net * 100.0) if revenue_net > 0 else 0.0

            # Clasificación del origen del stock vendido, según la PRIMERA COMPRA REAL
            # (recepción ligada a orden de compra). Se excluye la migración inicial
            # (recepciones sin OC), que si no haría que todo figure como "nuevo".
            #   * 'new': la primera compra real cae dentro del período.
            #   * 'replenished': primera compra previa al período + compra dentro del período.
            #   * 'old_stock': primera compra previa sin compra en el período, o vendido
            #     desde stock de apertura/migración (sin compra real registrada).
            fr = first_po_reception_map.get(pid)
            lrp = last_po_reception_in_period_map.get(pid)
            if fr and date_from <= fr <= date_to:
                stock_origin = 'new'
            elif fr and fr < date_from and lrp:
                stock_origin = 'replenished'
            elif fr and fr < date_from:
                stock_origin = 'old_stock'
            else:
                stock_origin = 'old_stock'

            ranking.append({
                'id': pid,
                'name': product.name or '',
                'code': product.default_code or '',
                'category': (product.categ_id.name if product.categ_id else ''),
                'revenue': revenue,
                'qty': qty,
                'cost': cost,
                'margin': margin,
                'margin_pct': margin_pct,
                'antiquity_days': antiquity_map[pid]['days'],
                'antiquity_source': antiquity_map[pid]['source'],
                'stock_origin': stock_origin,
                'first_purchase_date': fr.isoformat() if fr else '',
                'last_purchase_in_period': lrp.isoformat() if lrp else '',
            })
        ranking_by_rev = sorted(ranking, key=lambda x: x['revenue'], reverse=True)
        ranking_by_qty = sorted(ranking, key=lambda x: x['qty'], reverse=True)
        # Por antigüedad: del MÁS ANTIGUO (más días) al más nuevo.
        ranking_by_antiquity = sorted(ranking, key=lambda x: x['antiquity_days'], reverse=True)
        # Por margen (valor absoluto): del MÁS rentable al menos rentable.
        ranking_by_margin = sorted(ranking, key=lambda x: x['margin'], reverse=True)

        # ------------------------------------------------
        # Clasificación ABC (Pareto): basada en facturación acumulada
        #   A: 0 .. 80% acumulado
        #   B: 80 .. 95% acumulado
        #   C: 95 .. 100% acumulado
        # Como los items son los MISMOS dicts en todos los rankings, basta
        # con setear abc_class en cada item del ranking original.
        # ------------------------------------------------
        total_rev_for_abc = sum(r['revenue'] for r in ranking if r['revenue'] > 0)
        if total_rev_for_abc > 0:
            cum = 0.0
            for r in ranking_by_rev:
                rev = r['revenue']
                if rev <= 0:
                    r['abc_class'] = 'C'
                    r['cum_pct'] = 100.0
                    continue
                cum += rev
                cum_pct = (cum / total_rev_for_abc) * 100.0
                r['cum_pct'] = cum_pct
                if cum_pct <= 80.0:
                    r['abc_class'] = 'A'
                elif cum_pct <= 95.0:
                    r['abc_class'] = 'B'
                else:
                    r['abc_class'] = 'C'
        else:
            for r in ranking:
                r['abc_class'] = 'C'
                r['cum_pct'] = 0.0

        # Resumen ABC
        abc_summary = {
            'A': {'count': 0, 'revenue': 0.0, 'product_pct': 0.0, 'revenue_pct': 0.0},
            'B': {'count': 0, 'revenue': 0.0, 'product_pct': 0.0, 'revenue_pct': 0.0},
            'C': {'count': 0, 'revenue': 0.0, 'product_pct': 0.0, 'revenue_pct': 0.0},
        }
        for r in ranking:
            cls = r.get('abc_class', 'C')
            abc_summary[cls]['count'] += 1
            abc_summary[cls]['revenue'] += r.get('revenue', 0.0)
        total_products = sum(b['count'] for b in abc_summary.values())
        for b in abc_summary.values():
            b['product_pct'] = (b['count'] / total_products * 100.0) if total_products > 0 else 0.0
            b['revenue_pct'] = (b['revenue'] / total_rev_for_abc * 100.0) if total_rev_for_abc > 0 else 0.0

        # ------------------------------------------------
        # Resumen por categoría (acumulado del período, sin discriminar mes)
        # Orden: facturación desc, margen desc (tie-break).
        # ------------------------------------------------
        cat_agg = {}
        for r in ranking:
            pid = r['id']
            product = prod_info.get(pid)
            cat = product.categ_id if product else None
            cid = cat.id if cat and cat.id else 0
            cname = cat.name if cat and cat.id else 'Sin Categoría'
            entry = cat_agg.get(cid)
            if not entry:
                entry = {
                    'category_id': cid,
                    'name': cname,
                    'revenue': 0.0,
                    'cost': 0.0,
                    'margin': 0.0,
                    'qty': 0.0,
                    'product_count': 0,
                }
                cat_agg[cid] = entry
            entry['revenue'] += r.get('revenue', 0.0)
            entry['cost'] += r.get('cost', 0.0)
            entry['margin'] += r.get('margin', 0.0)
            entry['qty'] += r.get('qty', 0.0)
            entry['product_count'] += 1
        for entry in cat_agg.values():
            entry['margin_pct'] = ((entry['margin'] / entry['revenue']) * 100.0) if entry['revenue'] > 0 else 0.0
        category_summary = sorted(
            cat_agg.values(),
            key=lambda c: (c['revenue'], c['margin']),
            reverse=True,
        )

        # ------------------------------------------------
        # Origen del stock vendido (agregado por clasificación)
        # ------------------------------------------------
        origin_agg = {
            'new':         {'count': 0, 'revenue': 0.0, 'qty': 0.0, 'margin': 0.0, '_ant_sum': 0.0, '_ant_qty_sum': 0.0, '_ant_weight_sum': 0.0},
            'replenished': {'count': 0, 'revenue': 0.0, 'qty': 0.0, 'margin': 0.0, '_ant_sum': 0.0, '_ant_qty_sum': 0.0, '_ant_weight_sum': 0.0},
            'old_stock':   {'count': 0, 'revenue': 0.0, 'qty': 0.0, 'margin': 0.0, '_ant_sum': 0.0, '_ant_qty_sum': 0.0, '_ant_weight_sum': 0.0},
        }
        for r in ranking:
            cls = r.get('stock_origin') or 'old_stock'
            if cls not in origin_agg:
                cls = 'old_stock'
            ant = r.get('antiquity_days') or 0
            q = r.get('qty', 0.0) or 0.0
            origin_agg[cls]['count'] += 1
            origin_agg[cls]['revenue'] += r.get('revenue', 0.0)
            origin_agg[cls]['qty'] += q
            origin_agg[cls]['margin'] += r.get('margin', 0.0)
            origin_agg[cls]['_ant_sum'] += ant
            # Promedio ponderado por cantidad vendida (más representativo del stock que rotó)
            if q > 0:
                origin_agg[cls]['_ant_qty_sum'] += ant * q
                origin_agg[cls]['_ant_weight_sum'] += q
        total_origin_rev = sum(b['revenue'] for b in origin_agg.values())
        for b in origin_agg.values():
            b['revenue_pct'] = (b['revenue'] / total_origin_rev * 100.0) if total_origin_rev > 0 else 0.0
            b['margin_pct'] = (b['margin'] / b['revenue'] * 100.0) if b['revenue'] > 0 else 0.0
            # Promedio simple (por producto): suma de antigüedades / cantidad de productos
            b['avg_antiquity_days'] = (b['_ant_sum'] / b['count']) if b['count'] > 0 else 0.0
            # Promedio ponderado por cantidad vendida
            b['avg_antiquity_days_weighted'] = (
                (b['_ant_qty_sum'] / b['_ant_weight_sum']) if b['_ant_weight_sum'] > 0 else 0.0
            )
            # Limpiar las llaves auxiliares (prefijo _ no se serializa idiomáticamente)
            b.pop('_ant_sum', None)
            b.pop('_ant_qty_sum', None)
            b.pop('_ant_weight_sum', None)
        stock_origin_summary = {
            'period': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
            },
            'totals': {
                'product_count': sum(b['count'] for b in origin_agg.values()),
                'revenue': total_origin_rev,
            },
            'new': origin_agg['new'],
            'replenished': origin_agg['replenished'],
            'old_stock': origin_agg['old_stock'],
        }

        # Map producto -> categoria (para el modo group_by='category')
        prod_to_cat = {}
        cat_names = {}
        for pid in all_pids:
            product = prod_info.get(pid)
            if not product:
                continue
            cat = product.categ_id
            if cat and cat.id:
                prod_to_cat[pid] = cat.id
                cat_names[cat.id] = cat.name or 'Sin Categoría'
            else:
                prod_to_cat[pid] = 0
                cat_names[0] = 'Sin Categoría'

        # Ranking de CATEGORÍAS por revenue (para Top 8 + Otros cuando group_by='category')
        cat_rev_total = {}
        for pid in filtered_pids:
            cid = prod_to_cat.get(pid, 0)
            cat_rev_total[cid] = cat_rev_total.get(cid, 0.0) + prod_rev.get(pid, 0.0)
        sorted_cats = sorted(cat_rev_total.items(), key=lambda x: x[1], reverse=True)

        # ------------------------------------------------
        # Top N globales (sobre productos filtrados) + Otros
        # ------------------------------------------------
        TOP_N = top_n
        top_pids = [r['id'] for r in ranking_by_rev[:TOP_N]]
        top_pid_set = set(top_pids)
        top_cat_ids = [cid for cid, _ in sorted_cats[:TOP_N]]
        top_cat_set = set(top_cat_ids)

        # Coverage del Top N sobre el total del período (para mostrar en UI)
        total_period_revenue = sum(prod_rev.get(pid, 0.0) for pid in filtered_pids)
        if group_by == 'category':
            top_revenue_sum = sum(cat_rev_total.get(cid, 0.0) for cid in top_cat_ids)
        else:
            top_revenue_sum = sum(prod_rev.get(pid, 0.0) for pid in top_pids)
        coverage_pct = (top_revenue_sum / total_period_revenue * 100.0) if total_period_revenue > 0 else 0.0

        # ------------------------------------------------
        # Buckets mensuales sobre date_from .. date_to
        # ------------------------------------------------
        bucket_first = date_from.replace(day=1)
        bucket_last_start = date_to.replace(day=1)
        months_span = ((bucket_last_start.year - bucket_first.year) * 12
                       + (bucket_last_start.month - bucket_first.month) + 1)
        use_year_suffix = months_span > 12 or bucket_first.year != bucket_last_start.year
        label_fmt = '%b/%y' if use_year_suffix else '%b'

        buckets = []
        cursor = bucket_first
        while cursor <= bucket_last_start:
            bucket_end = cursor + relativedelta(months=1, days=-1)
            buckets.append((cursor, bucket_end))
            cursor = cursor + relativedelta(months=1)

        months_labels = [b[0].strftime(label_fmt) for b in buckets]
        months_ranges = [{'start': b[0].isoformat(), 'end': b[1].isoformat()} for b in buckets]

        # ------------------------------------------------
        # Desglose mensual: revenue por (segmento_top OR otros)
        # Segmento = producto o categoria segun group_by.
        # ------------------------------------------------
        if group_by == 'category':
            series = {cid: [0.0] * len(buckets) for cid in top_cat_ids}
        else:
            series = {pid: [0.0] * len(buckets) for pid in top_pids}
        others_series = [0.0] * len(buckets)
        total_per_month = [0.0] * len(buckets)

        for idx, (m_start, m_end) in enumerate(buckets):
            m_inv_dom = list(base_line_domain) + [
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.invoice_date', '>=', m_start),
                ('move_id.invoice_date', '<=', m_end),
            ]
            m_ref_dom = list(base_line_domain) + [
                ('move_id.move_type', '=', 'out_refund'),
                ('move_id.invoice_date', '>=', m_start),
                ('move_id.invoice_date', '<=', m_end),
            ]
            m_inv_g = self.env['account.move.line'].read_group(
                m_inv_dom, ['product_id', rev_field + ':sum'], ['product_id'])
            m_ref_g = self.env['account.move.line'].read_group(
                m_ref_dom, ['product_id', rev_field + ':sum'], ['product_id'])
            m_rev = self._signed_sum(m_inv_g, m_ref_g, 'product_id', rev_field)

            for pid, val in m_rev.items():
                if antiquity_bucket != 'all' and not in_bucket(antiquity_map.get(pid, {}).get('days', 0)):
                    continue
                total_per_month[idx] += val
                if group_by == 'category':
                    cid = prod_to_cat.get(pid, 0)
                    if cid in top_cat_set:
                        series[cid][idx] += val
                    else:
                        others_series[idx] += val
                else:
                    if pid in top_pid_set:
                        series[pid][idx] += val
                    else:
                        others_series[idx] += val

        # Empaquetar datasets segun el modo
        datasets = []
        if group_by == 'category':
            for cid in top_cat_ids:
                datasets.append({
                    '_kind': 'category',
                    'category_id': cid,
                    'product_id': 0,
                    'name': cat_names.get(cid, 'Sin Categoría'),
                    'code': '',
                    'data': series[cid],
                    'antiquity_days': None,
                    'antiquity_source': None,
                })
            datasets.append({
                '_kind': 'category',
                'category_id': 0,
                'product_id': 0,
                'name': 'Otros',
                'code': '',
                'data': others_series,
                'antiquity_days': None,
                'antiquity_source': 'others',
            })
        else:
            for r in ranking_by_rev[:TOP_N]:
                datasets.append({
                    '_kind': 'product',
                    'product_id': r['id'],
                    'category_id': 0,
                    'name': r['name'],
                    'code': r['code'],
                    'data': series[r['id']],
                    'antiquity_days': r['antiquity_days'],
                    'antiquity_source': r['antiquity_source'],
                })
            datasets.append({
                '_kind': 'product',
                'product_id': 0,
                'category_id': 0,
                'name': 'Otros',
                'code': '',
                'data': others_series,
                'antiquity_days': None,
                'antiquity_source': 'others',
            })

        # ------------------------------------------------
        # Comparativo año anterior (solo si preset == '12m_compare')
        # ------------------------------------------------
        previous_year = None
        if preset == '12m_compare':
            py_totals = []
            py_first = None
            py_last = None
            for (m_start, m_end) in buckets:
                py_start = m_start - relativedelta(years=1)
                py_end = m_end - relativedelta(years=1)
                if py_first is None:
                    py_first = py_start
                py_last = py_end
                py_inv_dom = list(base_line_domain)
                # Reemplazar el rango de fechas del dominio base
                py_inv_dom = [d for d in py_inv_dom
                              if not (isinstance(d, tuple) and d[0] in ('move_id.invoice_date',))]
                py_inv_dom += [
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('move_id.invoice_date', '>=', py_start),
                    ('move_id.invoice_date', '<=', py_end),
                ]
                py_ref_dom = list(py_inv_dom)
                py_ref_dom[-3] = ('move_id.move_type', '=', 'out_refund')

                py_inv_g = self.env['account.move.line'].read_group(
                    py_inv_dom, [rev_field + ':sum'], [])
                py_ref_g = self.env['account.move.line'].read_group(
                    py_ref_dom, [rev_field + ':sum'], [])
                inv_tot = (py_inv_g and (py_inv_g[0].get(rev_field) or 0.0)) or 0.0
                ref_tot = (py_ref_g and (py_ref_g[0].get(rev_field) or 0.0)) or 0.0
                py_totals.append(inv_tot - ref_tot)

            previous_year = {
                'total_per_month': py_totals,
                'period': {
                    'date_from': py_first.isoformat() if py_first else '',
                    'date_to': py_last.isoformat() if py_last else '',
                },
            }

        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }

        return {
            'currency': currency_info,
            'company': self._company_branding(),
            'period': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'preset': preset or 'custom',
            },
            'months': {
                'labels': months_labels,
                'ranges': months_ranges,
                'total_per_month': total_per_month,
            },
            'monthly_stack': {
                'datasets': datasets,
                'group_by': group_by,
                'top_n': TOP_N,
                'top_product_ids': list(top_pid_set),
                'top_category_ids': list(top_cat_set),
                'coverage_pct': coverage_pct,
            },
            'previous_year': previous_year,
            'ranking_by_revenue': ranking_by_rev[:20],
            'ranking_by_qty': ranking_by_qty[:20],
            'ranking_by_antiquity': ranking_by_antiquity[:20],
            'ranking_by_margin': ranking_by_margin[:20],
            'abc_summary': abc_summary,
            'category_summary': category_summary,
            'stock_origin_summary': stock_origin_summary,
            # ranking completo (sin slice) para que el frontend pueda filtrar por origen
            # sin perder productos. Si la lista crece mucho, considerá paginar.
            'all_ranking': ranking,
            'totals': {
                'product_count': len(filtered_pids),
                'total_revenue': sum(prod_rev.get(pid, 0.0) for pid in filtered_pids),
                'total_qty': sum(prod_qty.get(pid, 0.0) for pid in filtered_pids),
            },
            # Nota de exclusión por el criterio de mercadería (almacenable).
            'merchandise_filter': merchandise_filter,
            # Selector de compañía: opciones disponibles + selección efectiva.
            'companies': company_options,
            'selected_company_ids': selected_company_ids,
        }

    def _company_options(self):
        """Compañías que el usuario puede elegir en el selector del dashboard
        (las permitidas por su sesión). Se calcula ANTES de acotar el contexto."""
        return [{'id': c.id, 'name': c.name} for c in self.env.companies]

    def _effective_company_ids(self, filters):
        """
        Compañías efectivas para el dashboard = las pedidas por el selector,
        intersecadas con las permitidas (self.env.companies). Si no se pide
        ninguna (o ninguna válida), se usan TODAS las permitidas (= sumar todo).
        El resultado siempre es subconjunto de las permitidas (no amplía acceso).
        """
        allowed = self.env.companies.ids or [self.env.company.id]
        requested = (filters or {}).get('company_ids') or []
        try:
            requested = [int(c) for c in requested if c]
        except Exception:
            requested = []
        eff = [c for c in requested if c in allowed]
        return eff or allowed

    def _company_branding(self):
        """Datos de marca de la compañía activa para el encabezado (logo base64 + nombre)."""
        company = self.env.company
        logo = company.logo_web or company.logo
        if isinstance(logo, bytes):
            try:
                logo = logo.decode('ascii')
            except Exception:
                logo = ''
        return {
            'id': company.id,
            'name': company.name or '',
            'logo': logo or '',
        }

    # =====================================================================
    # Dashboard "Ventas por Gerencia" (vista diaria + comparativo YoY + proyección)
    # =====================================================================
    @api.model
    def get_sales_by_manager_data(self, filters=None):
        """
        Datos para el dashboard de Ventas por Gerencia/Vendedor (invoice_user_id).
        Mes seleccionado: ventas diarias por vendedor, comparativo trimestre actual
        vs mismo trimestre año anterior, proyección lineal del mes, participación.

        Filtros: year (opcional, default año actual), month (opcional, default mes actual).
        """
        if filters is None:
            filters = {}

        # INC-02: selector de compañía (consolida/filtra vía allowed_company_ids).
        company_options = self._company_options()
        selected_company_ids = sorted(self._effective_company_ids(filters))
        self = self.with_context(allowed_company_ids=selected_company_ids)

        today = fields.Date.today()
        # Rango de fechas: si vienen date_from/date_to se usan; si no, mes actual
        # (o el indicado por year/month, para compatibilidad).
        df = self._as_date(filters.get('date_from'), None)
        dt = self._as_date(filters.get('date_to'), None)
        if df and dt and dt >= df:
            m_start, m_end = df, dt
        else:
            try:
                year = int(filters.get('year') or today.year)
                month = int(filters.get('month') or today.month)
            except Exception:
                year, month = today.year, today.month
            m_start = datetime.date(year, month, 1)
            m_end = m_start + relativedelta(months=1, days=-1)

        # year/month siempre definidos (compatibilidad con el resto del método).
        year, month = m_start.year, m_start.month

        # Si el período incluye hoy, los datos se cortan en hoy (período en curso).
        if m_start <= today <= m_end:
            is_current_period = True
            m_end_data = today
        else:
            is_current_period = False
            m_end_data = m_end

        # Agrupación de la tabla: por día si el rango cae en un único mes
        # calendario; por mes si abarca más de un mes.
        group_mode = 'day' if (m_start.year == m_end.year and m_start.month == m_end.month) else 'month'

        company = self.env.company
        company_currency = company.currency_id
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

        # ========== Dominios base ==========
        base_move_domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', m_start),
            ('invoice_date', '<=', m_end_data),
            ('company_id', 'in', selected_company_ids),  # INC-02
        ]
        inv_domain = base_move_domain + [('move_type', '=', 'out_invoice')]
        ref_domain = base_move_domain + [('move_type', '=', 'out_refund')]

        # ========== Vendedores con ventas en el mes ==========
        inv_user_g = self.env['account.move'].read_group(
            inv_domain, ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        ref_user_g = self.env['account.move'].read_group(
            ref_domain, ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        user_net = self._signed_sum(inv_user_g, ref_user_g, 'invoice_user_id')

        users_ordered = sorted(user_net.items(), key=lambda x: x[1], reverse=True)
        managers = []
        for uid, amt in users_ordered:
            if not uid:
                continue
            name = self._name_of(inv_user_g, 'invoice_user_id', uid) \
                or self._name_of(ref_user_g, 'invoice_user_id', uid) \
                or self.env['res.users'].browse(uid).name
            managers.append({'id': uid, 'name': name or 'Sin asignar', 'total': amt})

        # ========== Desglose por vendedor (por día o por mes) ==========
        # group_mode='day': una columna por día con ventas.
        # group_mode='month': una columna por mes del rango (estilo resumen).
        moves = self.env['account.move'].search(base_move_domain)
        bucket_map = {}  # key(date) -> {uid -> amount}
        keys_with_sales = set()
        for m in moves:
            d = m.invoice_date
            if not d:
                continue
            key = d if group_mode == 'day' else datetime.date(d.year, d.month, 1)
            uid = m.invoice_user_id.id if m.invoice_user_id else 0
            sign = -1 if m.move_type == 'out_refund' else 1
            amt = sign * self._convert_amount(
                m.amount_total, m.currency_id, company_currency,
                m.company_id, d)
            bucket = bucket_map.setdefault(key, {})
            bucket[uid] = bucket.get(uid, 0.0) + amt
            keys_with_sales.add(key)

        if group_mode == 'day':
            # Solo días con al menos una factura
            sorted_keys = sorted(keys_with_sales)
            labels = ['%d-%s' % (k.day, MESES_ES[k.month - 1]) for k in sorted_keys]
        else:
            # Todos los meses del rango (aunque alguno no tenga ventas)
            sorted_keys = []
            cursor = datetime.date(m_start.year, m_start.month, 1)
            last = datetime.date(m_end.year, m_end.month, 1)
            while cursor <= last:
                sorted_keys.append(cursor)
                cursor = cursor + relativedelta(months=1)
            labels = [_month_label_es(k) for k in sorted_keys]

        # Tabla: por vendedor + fila TOTAL
        daily_table = {
            'days': [k.isoformat() for k in sorted_keys],
            'labels': labels,
            'group_mode': group_mode,
            'rows': [],          # por vendedor
            'total_per_day': [], # por columna (día o mes)
        }
        for k in sorted_keys:
            daily_table['total_per_day'].append(sum(bucket_map.get(k, {}).values()))
        # Cada vendedor: serie de montos por columna
        for mgr in managers:
            row = {
                'id': mgr['id'],
                'name': mgr['name'],
                'amounts': [bucket_map.get(k, {}).get(mgr['id'], 0.0) for k in sorted_keys],
                'total': mgr['total'],
            }
            # USD aproximado por vendedor (con tipo al cierre del período)
            if usd_currency and company_currency and company_currency != usd_currency:
                row['total_usd'] = company_currency._convert(
                    mgr['total'], usd_currency, company, m_end_data)
            else:
                row['total_usd'] = mgr['total']
            daily_table['rows'].append(row)

        total_month = sum(mgr['total'] for mgr in managers)
        total_usd = 0.0
        if usd_currency and company_currency and company_currency != usd_currency:
            total_usd = company_currency._convert(total_month, usd_currency, company, m_end_data)
        else:
            total_usd = total_month

        def _to_usd(amount, ref_date):
            if usd_currency and company_currency and company_currency != usd_currency:
                return company_currency._convert(amount, usd_currency, company, ref_date)
            return amount

        def _net_total_in_range(d_from, d_to):
            _co = [('company_id', 'in', selected_company_ids)]
            inv_g = self.env['account.move'].read_group(
                [('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
                 ('invoice_date', '>=', d_from), ('invoice_date', '<=', d_to)] + _co,
                ['amount_total:sum'], [])
            ref_g = self.env['account.move'].read_group(
                [('move_type', '=', 'out_refund'), ('state', '=', 'posted'),
                 ('invoice_date', '>=', d_from), ('invoice_date', '<=', d_to)] + _co,
                ['amount_total:sum'], [])
            inv_t = (inv_g and (inv_g[0].get('amount_total') or 0)) or 0
            ref_t = (ref_g and (ref_g[0].get('amount_total') or 0)) or 0
            return inv_t - ref_t

        # ========== Comparativo: período actual vs mismo período año anterior ==========
        cur_total = _net_total_in_range(m_start, m_end_data)
        prev_start = m_start - relativedelta(years=1)
        prev_end = m_end_data - relativedelta(years=1)
        prev_total = _net_total_in_range(prev_start, prev_end)
        change_pct = ((cur_total - prev_total) / prev_total * 100.0) if prev_total > 0 else 0.0

        if m_start.year == m_end.year:
            cur_cmp_label = str(m_start.year)
            prev_cmp_label = str(m_start.year - 1)
        else:
            cur_cmp_label = '%d-%d' % (m_start.year, m_end.year)
            prev_cmp_label = '%d-%d' % (m_start.year - 1, m_end.year - 1)

        comparative_quarter = {
            'current_label': cur_cmp_label,
            'previous_label': prev_cmp_label,
            'current_total': cur_total,
            'previous_total': prev_total,
            'change_pct': change_pct,
            # INC-04: si el período anterior está vacío o casi sin datos, el % es
            # engañoso (no es crecimiento real). El frontend debe avisar en vez del %.
            'prev_incomplete': bool(prev_total <= 0 or (cur_total > 0 and prev_total < cur_total * 0.25)),
        }

        # ========== Proyección lineal del período ==========
        total_days = (m_end - m_start).days + 1
        days_elapsed = (m_end_data - m_start).days + 1 if is_current_period else total_days
        if days_elapsed < 1:
            days_elapsed = 1
        factor = (total_days / days_elapsed) if days_elapsed > 0 else 1.0
        projection_total = total_month * factor

        projection_by_mgr = []
        for mgr in managers:
            proj = mgr['total'] * factor
            projection_by_mgr.append({
                'id': mgr['id'],
                'name': mgr['name'],
                'projection': proj,
                'projection_usd': _to_usd(proj, m_end_data),
            })
        projection_total_usd = _to_usd(projection_total, m_end_data)

        # ---- Período anterior equivalente (mismo nº de días, inmediatamente antes) ----
        prev_p_end = m_start - relativedelta(days=1)
        prev_p_start = prev_p_end - relativedelta(days=total_days - 1)
        prev_dom = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', prev_p_start),
            ('invoice_date', '<=', prev_p_end),
        ]
        prev_inv_g = self.env['account.move'].read_group(
            prev_dom + [('move_type', '=', 'out_invoice')],
            ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        prev_ref_g = self.env['account.move'].read_group(
            prev_dom + [('move_type', '=', 'out_refund')],
            ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        prev_user_net = self._signed_sum(prev_inv_g, prev_ref_g, 'invoice_user_id')
        prev_period_total = sum(prev_user_net.values())

        for entry in projection_by_mgr:
            prev_amt = prev_user_net.get(entry['id'], 0.0)
            entry['prev_month'] = prev_amt
            entry['prev_month_usd'] = _to_usd(prev_amt, prev_p_end)

        prev_period_total_usd = _to_usd(prev_period_total, prev_p_end)
        ratio_pct = (projection_total / prev_period_total * 100.0) if prev_period_total > 0 else 0.0

        # Etiqueta del período anterior para la tabla de proyección
        if group_mode == 'day' and prev_p_start.month == prev_p_end.month:
            prev_label_proj = MESES_ES[prev_p_start.month - 1].capitalize()
        else:
            prev_label_proj = 'Per. ant.'

        projection = {
            'total_days_month': total_days,
            'days_elapsed': days_elapsed,
            'progress_pct': (days_elapsed / total_days * 100.0) if total_days > 0 else 0.0,
            'projection_total': projection_total,
            'projection_total_usd': projection_total_usd,
            'by_manager': projection_by_mgr,
            'prev_month_label': prev_label_proj,
            'prev_month_total': prev_period_total,
            'prev_month_total_usd': prev_period_total_usd,
            'ratio_pct': ratio_pct,
            # INC-04: la proyección solo tiene sentido en un ÚNICO mes en curso.
            # Con rango multi-mes o período cerrado, el frontend debe ocultarla.
            'applies': bool(group_mode == 'day' and is_current_period),
        }

        # ========== Participación por vendedor (donut) ==========
        participation = []
        for mgr in managers:
            pct = (mgr['total'] / total_month * 100.0) if total_month > 0 else 0.0
            participation.append({
                'id': mgr['id'],
                'name': mgr['name'],
                'amount': mgr['total'],
                'pct': pct,
            })

        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }

        return {
            'currency': currency_info,
            'company': self._company_branding(),
            'companies': company_options,
            'selected_company_ids': selected_company_ids,
            'period': {
                'year': year,
                'month': month,
                'date_from': m_start.isoformat(),
                'date_to': m_end.isoformat(),
                'date_to_data': m_end_data.isoformat(),
                'is_current_month': is_current_period,
                'group_mode': group_mode,
            },
            'managers': managers,
            'daily_table': daily_table,
            'totals': {
                'total_gs': total_month,
                'total_usd': total_usd,
            },
            'comparative_quarter': comparative_quarter,
            'projection': projection,
            'participation': participation,
        }

    # =====================================================================
    # Dashboard "Resumen Mensual"
    # =====================================================================
    @api.model
    def get_monthly_summary_data(self, filters=None):
        """
        Datos para el dashboard de Resumen Mensual. Evolución mensual del
        total facturado + agregado por vendedor (invoice_user_id) por mes.
        Devuelve también stats: promedio, mejor mes, peor mes.

        Filtros: preset (default 12m).
        """
        if filters is None:
            filters = {}

        # INC-02: selector de compañía (consolida/filtra vía allowed_company_ids).
        company_options = self._company_options()
        selected_company_ids = sorted(self._effective_company_ids(filters))
        self = self.with_context(allowed_company_ids=selected_company_ids)

        today = fields.Date.today()
        # INC-06: el filtro de fecha de la interfaz tiene prioridad. Solo si NO viene
        # un rango explícito se usa el preset (default 12m).
        df = self._as_date(filters.get('date_from'), None)
        dt = self._as_date(filters.get('date_to'), None)
        if df and dt and dt >= df:
            date_from, date_to = df, dt
        else:
            preset = (filters.get('preset') or '12m').lower()
            p_from, p_to = self._resolve_period_preset(preset, today)
            if p_from and p_to:
                date_from, date_to = p_from, p_to
            else:
                date_from = df or (today.replace(day=1) - relativedelta(months=11))
                date_to = dt or (today.replace(day=1) + relativedelta(months=1, days=-1))

        company = self.env.company
        company_currency = company.currency_id

        # ========== Buckets mensuales ==========
        bucket_first = date_from.replace(day=1)
        bucket_last_start = date_to.replace(day=1)
        buckets = []
        cursor = bucket_first
        while cursor <= bucket_last_start:
            bucket_end = cursor + relativedelta(months=1, days=-1)
            buckets.append((cursor, bucket_end))
            cursor = cursor + relativedelta(months=1)

        months_labels = [_month_label_es(b[0]) for b in buckets]
        months_ranges = [{'start': b[0].isoformat(), 'end': b[1].isoformat()} for b in buckets]

        # ========== Todos los vendedores con ventas en el período ==========
        period_dom = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('company_id', 'in', selected_company_ids),  # INC-02
        ]
        inv_dom = period_dom + [('move_type', '=', 'out_invoice')]
        ref_dom = period_dom + [('move_type', '=', 'out_refund')]
        inv_u_g = self.env['account.move'].read_group(
            inv_dom, ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        ref_u_g = self.env['account.move'].read_group(
            ref_dom, ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
        user_total = self._signed_sum(inv_u_g, ref_u_g, 'invoice_user_id')

        users_ordered = sorted([(uid, t) for uid, t in user_total.items() if uid],
                               key=lambda x: x[1], reverse=True)
        managers_meta = []
        for uid, total in users_ordered:
            name = self._name_of(inv_u_g, 'invoice_user_id', uid) \
                or self._name_of(ref_u_g, 'invoice_user_id', uid) \
                or self.env['res.users'].browse(uid).name
            managers_meta.append({'id': uid, 'name': name or 'Sin asignar', 'total': total})

        # ========== Para cada mes, monto por vendedor ==========
        # Matriz: manager x mes
        manager_monthly = {m['id']: [0.0] * len(buckets) for m in managers_meta}
        total_monthly = [0.0] * len(buckets)

        for idx, (m_start, m_end) in enumerate(buckets):
            month_dom = period_dom[:2] + [
                ('invoice_date', '>=', m_start),
                ('invoice_date', '<=', m_end),
            ]
            m_inv_g = self.env['account.move'].read_group(
                month_dom + [('move_type', '=', 'out_invoice')],
                ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
            m_ref_g = self.env['account.move'].read_group(
                month_dom + [('move_type', '=', 'out_refund')],
                ['invoice_user_id', 'amount_total:sum'], ['invoice_user_id'])
            m_user = self._signed_sum(m_inv_g, m_ref_g, 'invoice_user_id')
            for uid, amt in m_user.items():
                if uid in manager_monthly:
                    manager_monthly[uid][idx] = amt
                total_monthly[idx] += amt

        # ========== Stats ==========
        total_period = sum(total_monthly)
        avg_month = (total_period / len(total_monthly)) if total_monthly else 0.0

        best_idx = max(range(len(total_monthly)), key=lambda i: total_monthly[i]) \
            if total_monthly else None
        worst_idx = min(range(len(total_monthly)), key=lambda i: total_monthly[i]) \
            if total_monthly else None
        best_month = {'label': months_labels[best_idx], 'amount': total_monthly[best_idx]} \
            if best_idx is not None else None
        worst_month = {'label': months_labels[worst_idx], 'amount': total_monthly[worst_idx]} \
            if worst_idx is not None else None

        # ========== Armar respuesta ==========
        rows = []
        for m in managers_meta:
            pct_total = (m['total'] / total_period * 100.0) if total_period > 0 else 0.0
            rows.append({
                'id': m['id'],
                'name': m['name'],
                'monthly': manager_monthly[m['id']],
                'total': m['total'],
                'pct': pct_total,
            })

        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }

        return {
            'currency': currency_info,
            'company': self._company_branding(),
            'companies': company_options,
            'selected_company_ids': selected_company_ids,
            'period': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'preset': (filters.get('preset') or 'custom'),
                'months': len(buckets),
            },
            'months': {
                'labels': months_labels,
                'ranges': months_ranges,
            },
            'monthly_total': total_monthly,
            'rows': rows,
            'totals': {
                'total_period': total_period,
                'avg_month': avg_month,
                'best_month': best_month,
                'worst_month': worst_month,
            },
        }

    # =====================================================================
    # Dashboard de COMPRAS
    # =====================================================================
    @api.model
    def get_purchase_dashboard_data(self, filters=None):
        """
        Datos del Dashboard de Compras. Fuente: account.move posteadas
        con move_type in ('in_invoice', 'in_refund'). Las notas de crédito
        (in_refund) restan del total.

        Devuelve:
          - kpis: total invertido, # facturas, # proveedores, # productos.
          - monthly: labels, purchases[], sales[] (para comparativo).
          - top_suppliers: top 10 proveedores por monto neto.
          - top_products: top 10 productos comprados por monto neto.
          - category_summary: agregado por categoría (monto, qty, # SKUs).

        Filtros: preset, date_from, date_to.
        """
        if filters is None:
            filters = {}

        # Selector de compañía (ver get_product_dashboard_data). Vacío/ambas = suma todo.
        company_options = self._company_options()
        selected_company_ids = self._effective_company_ids(filters)
        # env.company = primer elemento de allowed_company_ids en Odoo 18, así que
        # ordenamos ascendente: la compañía de referencia para el costo único es la
        # de menor id (MATRIZ cuando están ambas). Determinístico sin importar la sesión.
        selected_company_ids = sorted(selected_company_ids)
        self = self.with_context(allowed_company_ids=selected_company_ids)

        # Check de IVA para la línea de ventas (comparativo). Las compras son COSTO
        # (valorización), que no lleva IVA: no se ven afectadas por este check.
        sales_field = 'price_total' if filters.get('tax_included') else 'price_subtotal'

        today = fields.Date.today()
        preset = (filters.get('preset') or '').lower()
        p_from, p_to = self._resolve_period_preset(preset, today)
        if p_from and p_to:
            date_from = p_from
            date_to = p_to
        else:
            default_to = today.replace(day=1) + relativedelta(months=1, days=-1)
            default_from = today.replace(day=1) - relativedelta(months=5)
            date_from = self._as_date(filters.get('date_from'), default_from)
            date_to = self._as_date(filters.get('date_to'), default_to)

        company_currency = self.env.company.currency_id
        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }

        # Dominios base
        base_move_domain = [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        inv_domain = base_move_domain + [('move_type', '=', 'in_invoice')]
        ref_domain = base_move_domain + [('move_type', '=', 'in_refund')]

        # ========== KPIs ==========
        moves = self.env['account.move'].search(base_move_domain)
        total_invested = sum(self._move_amount_in_company(m, company_currency) for m in moves)
        invoice_count = len([m for m in moves if m.move_type == 'in_invoice'])
        supplier_ids = list(set(m.partner_id.id for m in moves if m.partner_id))
        supplier_count = len(supplier_ids)

        # ========== Fuente de COMPRAS: mercadería RECIBIDA valorizada (ligada a OC) ==========
        # Refleja la compra/importación real (costo + landed costs), no las líneas de
        # factura (que para importaciones traen ~100M, irreal). Excluye el stock inicial
        # de la migración (no ligado a OC). Detalle en _received_merchandise.
        received = self._received_merchandise(date_from, date_to)
        compras_mercaderia = received['total']
        top_suppliers = received['by_supplier']
        top_products = received['by_product']
        category_summary = received['by_category']
        product_count = received['product_count']
        if received['supplier_count']:
            supplier_count = received['supplier_count']

        # GASTOS (servicios / no mercadería) desde facturas de proveedor, como referencia.
        gastos_line_domain = [
            ('parent_state', '=', 'posted'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to),
            ('display_type', '=', 'product'),
        ]
        merchandise_filter = self._merchandise_exclusion(
            gastos_line_domain, 'in_invoice', 'in_refund')
        gastos_total = merchandise_filter['amount']
        # Nota: las compras se valorizan por mercadería recibida (costo/landed). Las
        # facturas/precios de OC pueden estar incompletos (OC con monto simbólico).
        merchandise_filter['compras_note'] = (
            'Compras = mercadería recibida valorizada (costo + landed costs), ligada a '
            'órdenes de compra. Incluye importaciones; excluye el stock inicial de '
            'migración. Las facturas de proveedor / precios de OC pueden estar incompletos.')

        # ========== Tendencia mensual (compras y ventas) ==========
        bucket_first = date_from.replace(day=1)
        bucket_last_start = date_to.replace(day=1)
        months_span = ((bucket_last_start.year - bucket_first.year) * 12 +
                       (bucket_last_start.month - bucket_first.month) + 1)
        use_year_suffix = months_span > 12 or bucket_first.year != bucket_last_start.year
        label_fmt = '%b/%y' if use_year_suffix else '%b'

        buckets = []
        cursor = bucket_first
        while cursor <= bucket_last_start:
            bucket_end = cursor + relativedelta(months=1, days=-1)
            buckets.append((cursor, bucket_end))
            cursor = cursor + relativedelta(months=1)

        months_labels = [b[0].strftime(label_fmt) for b in buckets]
        months_ranges = [{'start': b[0].isoformat(), 'end': b[1].isoformat()} for b in buckets]

        # Compras = mercadería recibida valorizada por mes (ligada a OC). Ventas =
        # mercadería vendida neta (facturas), como comparativo.
        by_month = received['by_month']
        purchases_monthly = []
        sales_monthly = []
        for m_start, m_end in buckets:
            # Compras de mercadería recibida valorizada del mes
            purchases_monthly.append(by_month.get(m_start.strftime('%Y-%m'), 0.0))

            mbase = [('parent_state', '=', 'posted'),
                     ('display_type', '=', 'product'),
                     ('move_id.invoice_date', '>=', m_start),
                     ('move_id.invoice_date', '<=', m_end)] + self._MERCHANDISE_LEAVES
            # Ventas de mercadería (comparativo) — respeta el check de IVA.
            s_inv = self.env['account.move.line'].read_group(
                mbase + [('move_id.move_type', '=', 'out_invoice')], [sales_field + ':sum'], [])
            s_ref = self.env['account.move.line'].read_group(
                mbase + [('move_id.move_type', '=', 'out_refund')], [sales_field + ':sum'], [])
            sales_monthly.append(
                ((s_inv[0].get(sales_field) if s_inv else 0) or 0)
                - ((s_ref[0].get(sales_field) if s_ref else 0) or 0))

        return {
            'currency': currency_info,
            'company': self._company_branding(),
            'period': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'preset': preset or 'custom',
            },
            'kpis': {
                'total_invested': total_invested,
                # Compras de mercadería (almacenable), neto sin impuestos.
                'compras_mercaderia': compras_mercaderia,
                # Gastos: líneas que no son mercadería (servicios/no almacenable/sin producto).
                'gastos': gastos_total,
                'invoice_count': invoice_count,
                'supplier_count': supplier_count,
                'product_count': product_count,
            },
            # Nota de exclusión por el criterio de mercadería (almacenable).
            'merchandise_filter': merchandise_filter,
            # Selector de compañía: opciones disponibles + selección efectiva.
            'companies': company_options,
            'selected_company_ids': selected_company_ids,
            'monthly': {
                'labels': months_labels,
                'ranges': months_ranges,
                'purchases': purchases_monthly,
                'sales': sales_monthly,
            },
            'top_suppliers': top_suppliers,
            'top_products': top_products,
            'category_summary': category_summary,
        }

    # =====================================================================
    # Insights automáticos
    # =====================================================================
    @api.model
    def get_dashboard_insights(self, filters=None):
        """
        Detecta cambios significativos del período actual vs el período anterior
        (de misma duración, inmediatamente antes) y emite insights accionables.

        Devuelve hasta 10 insights ordenados por relevancia. Cada insight es:
          {
            'type': 'positive'|'negative'|'warning'|'info',
            'icon': '...',           # icono FontAwesome
            'title': '...',
            'description': '...',
            'metric': '...',         # texto formateado
            'category_id': int|None, # para drill
          }
        """
        if filters is None:
            filters = {}

        # Selector de compañía: consistente con el resto del dashboard.
        _eff = sorted(self._effective_company_ids(filters))
        self = self.with_context(allowed_company_ids=_eff)

        today = fields.Date.today()

        # Período actual (mismo cálculo que el endpoint principal)
        preset = (filters.get('preset') or '').lower()
        p_from, p_to = self._resolve_period_preset(preset, today)
        if p_from and p_to:
            date_from = p_from
            date_to = p_to
        else:
            default_to = today.replace(day=1) + relativedelta(months=1, days=-1)
            default_from = today.replace(day=1) - relativedelta(months=5)
            date_from = self._as_date(filters.get('date_from'), default_from)
            date_to = self._as_date(filters.get('date_to'), default_to)

        # Período anterior: misma duración inmediatamente antes
        period_days = (date_to - date_from).days
        prev_to = date_from - datetime.timedelta(days=1)
        prev_from = prev_to - datetime.timedelta(days=period_days)

        # Dominios base
        def _line_dom(d_from, d_to, move_type):
            return [
                ('parent_state', '=', 'posted'),
                ('display_type', '=', 'product'),
                ('move_id.invoice_date', '>=', d_from),
                ('move_id.invoice_date', '<=', d_to),
                ('move_id.move_type', '=', move_type),
            ]

        # Facturación por producto: actual y anterior
        cur_inv = self.env['account.move.line'].read_group(
            _line_dom(date_from, date_to, 'out_invoice'),
            ['product_id', 'price_total:sum', 'quantity:sum'], ['product_id'])
        cur_ref = self.env['account.move.line'].read_group(
            _line_dom(date_from, date_to, 'out_refund'),
            ['product_id', 'price_total:sum', 'quantity:sum'], ['product_id'])
        cur_rev = self._signed_sum(cur_inv, cur_ref, 'product_id', 'price_total')
        cur_qty = self._signed_sum(cur_inv, cur_ref, 'product_id', 'quantity')

        prev_inv = self.env['account.move.line'].read_group(
            _line_dom(prev_from, prev_to, 'out_invoice'),
            ['product_id', 'price_total:sum', 'quantity:sum'], ['product_id'])
        prev_ref = self.env['account.move.line'].read_group(
            _line_dom(prev_from, prev_to, 'out_refund'),
            ['product_id', 'price_total:sum', 'quantity:sum'], ['product_id'])
        prev_rev = self._signed_sum(prev_inv, prev_ref, 'product_id', 'price_total')
        prev_qty = self._signed_sum(prev_inv, prev_ref, 'product_id', 'quantity')

        all_pids = list(set(list(cur_rev.keys()) + list(prev_rev.keys())))

        if not all_pids:
            return {
                'period': {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()},
                'prev_period': {'date_from': prev_from.isoformat(), 'date_to': prev_to.isoformat()},
                'insights': [],
            }

        prods = self.env['product.product'].browse(all_pids)
        prods.read(['name', 'categ_id', 'standard_price'])
        prod_info = {p.id: p for p in prods}

        # Agregar por categoría (cur y prev)
        cat_map = {}
        for pid, rev in cur_rev.items():
            product = prod_info.get(pid)
            if not product:
                continue
            cat = product.categ_id
            cid = cat.id if cat else 0
            cname = cat.name if cat else 'Sin Categoría'
            if cid not in cat_map:
                cat_map[cid] = {'name': cname, 'cur_rev': 0.0, 'prev_rev': 0.0,
                                'cur_cost': 0.0, 'prev_cost': 0.0}
            cat_map[cid]['cur_rev'] += rev
            cat_map[cid]['cur_cost'] += (product.standard_price or 0.0) * cur_qty.get(pid, 0.0)
        for pid, rev in prev_rev.items():
            product = prod_info.get(pid)
            if not product:
                continue
            cat = product.categ_id
            cid = cat.id if cat else 0
            cname = cat.name if cat else 'Sin Categoría'
            if cid not in cat_map:
                cat_map[cid] = {'name': cname, 'cur_rev': 0.0, 'prev_rev': 0.0,
                                'cur_cost': 0.0, 'prev_cost': 0.0}
            cat_map[cid]['prev_rev'] += rev
            cat_map[cid]['prev_cost'] += (product.standard_price or 0.0) * prev_qty.get(pid, 0.0)

        insights = []

        # ===== Cambio total de facturación =====
        cur_total = sum(cur_rev.values())
        prev_total = sum(prev_rev.values())
        if prev_total > 0:
            total_change = (cur_total - prev_total) / prev_total * 100
            if abs(total_change) >= 10:
                insights.append({
                    'type': 'positive' if total_change > 0 else 'negative',
                    'icon': 'fa-arrow-up' if total_change > 0 else 'fa-arrow-down',
                    'title': ('Facturación total subió %.1f%%' % total_change)
                             if total_change > 0
                             else ('Facturación total cayó %.1f%%' % abs(total_change)),
                    'description': 'vs período anterior de misma duración',
                    'metric': ('+%.1f%%' if total_change > 0 else '%.1f%%') % total_change,
                    'category_id': None,
                    '_priority': abs(total_change),  # más cambio = más relevante
                })

        # ===== Margen promedio: % actual vs % anterior =====
        cur_cost_total = sum(cat_map[cid]['cur_cost'] for cid in cat_map)
        prev_cost_total = sum(cat_map[cid]['prev_cost'] for cid in cat_map)
        cur_margin_pct = ((cur_total - cur_cost_total) / cur_total * 100) if cur_total > 0 else 0
        prev_margin_pct = ((prev_total - prev_cost_total) / prev_total * 100) if prev_total > 0 else 0
        margin_change_pp = cur_margin_pct - prev_margin_pct
        if prev_total > 0 and abs(margin_change_pp) >= 2:
            insights.append({
                'type': 'positive' if margin_change_pp > 0 else 'warning',
                'icon': 'fa-percent',
                'title': 'Margen promedio %s %.1f pp' % (
                    'subió' if margin_change_pp > 0 else 'bajó', abs(margin_change_pp)),
                'description': 'Pasó de %.1f%% a %.1f%%' % (prev_margin_pct, cur_margin_pct),
                'metric': '%+.1f pp' % margin_change_pp,
                'category_id': None,
                '_priority': abs(margin_change_pp) * 10,
            })

        # ===== Categorías con cambio significativo (>= 30%) =====
        for cid, d in cat_map.items():
            cur, prev = d['cur_rev'], d['prev_rev']
            if prev <= 0 or cur <= 0:
                continue
            change = (cur - prev) / prev * 100
            if abs(change) < 30:
                continue
            insights.append({
                'type': 'positive' if change > 0 else 'negative',
                'icon': 'fa-arrow-up' if change > 0 else 'fa-arrow-down',
                'title': '%s %s %.0f%%' % (
                    d['name'], 'creció' if change > 0 else 'cayó', abs(change)),
                'description': 'Facturación: actual vs período anterior',
                'metric': '%+.1f%%' % change,
                'category_id': cid,
                '_priority': abs(change),
            })

        # ===== Concentración Pareto (top 20% de productos = % facturación) =====
        if cur_total > 0:
            sorted_prods = sorted(cur_rev.items(), key=lambda x: x[1], reverse=True)
            n = len(sorted_prods)
            top20_count = max(1, int(n * 0.2))
            top20_rev = sum(r for _, r in sorted_prods[:top20_count])
            top20_pct = (top20_rev / cur_total * 100) if cur_total > 0 else 0
            if top20_pct >= 80:
                # Concentración tipo Pareto pronunciada
                insights.append({
                    'type': 'info',
                    'icon': 'fa-bullseye',
                    'title': 'Top 20%% de productos = %.0f%% de facturación' % top20_pct,
                    'description': '%d SKUs concentran lo principal del negocio (Pareto)' % top20_count,
                    'metric': '%.0f%%' % top20_pct,
                    'category_id': None,
                    '_priority': top20_pct - 70,
                })

        # ===== Alerta de Stock Muerto (necesita stock.quant) =====
        if 'stock.quant' in self.env:
            try:
                # Capital total con stock (respeta conmutador de compañías;
                # excluye archivados para ser consistente con el bloque de stock).
                company_ids = self.env.companies.ids or [self.env.company.id]
                self.env.cr.execute('''
                    SELECT sq.product_id, SUM(sq.quantity) AS qty
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    JOIN product_product pp ON pp.id = sq.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE sl.usage = 'internal'
                      AND sl.company_id IN %s
                      AND pt.active = TRUE
                    GROUP BY sq.product_id
                    HAVING SUM(sq.quantity) > 0
                ''', (tuple(company_ids),))
                stock_rows = self.env.cr.dictfetchall()
                stock_map = {r['product_id']: float(r['qty'] or 0.0) for r in stock_rows}
                pids = list(stock_map.keys())

                if pids:
                    s_prods = self.env['product.product'].browse(pids)
                    s_prods.read(['standard_price'])
                    capital_total = sum((p.standard_price or 0.0) * stock_map.get(p.id, 0.0)
                                        for p in s_prods)
                    # Productos sin movimiento en el período
                    no_movement_pids = [pid for pid in pids if pid not in cur_rev]
                    capital_no_move = sum((prod_info.get(pid) or s_prods.browse(pid)).standard_price
                                          * stock_map.get(pid, 0.0)
                                          for pid in no_movement_pids
                                          if (prod_info.get(pid) or s_prods.browse(pid)).standard_price)
                    if capital_total > 0:
                        pct_dead = capital_no_move / capital_total * 100
                        if pct_dead >= 30:
                            insights.append({
                                'type': 'warning',
                                'icon': 'fa-exclamation-triangle',
                                'title': 'Stock muerto = %.0f%% del capital con stock' % pct_dead,
                                'description': '%d SKUs sin movimiento en el período' % len(no_movement_pids),
                                'metric': '%.0f%%' % pct_dead,
                                'category_id': None,
                                '_priority': pct_dead,
                            })
            except Exception:
                pass

        # ===== Productos "resucitados": vendieron este período después de mucho tiempo =====
        revived_count = 0
        if 'stock.move' in self.env and cur_rev:
            try:
                cur_pids = list(cur_rev.keys())
                # Última venta antes del período actual
                self.env.cr.execute('''
                    SELECT aml.product_id, MAX(am.invoice_date) AS last_pre
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    WHERE am.state = 'posted'
                      AND am.move_type = 'out_invoice'
                      AND am.invoice_date < %s
                      AND aml.product_id IN %s
                    GROUP BY aml.product_id
                ''', (date_from, tuple(cur_pids),))
                for row in self.env.cr.dictfetchall():
                    lp = row['last_pre']
                    if isinstance(lp, str):
                        lp = fields.Date.from_string(lp)
                    if lp and (date_from - lp).days >= 365:
                        revived_count += 1
            except Exception:
                pass
            if revived_count >= 3:
                insights.append({
                    'type': 'info',
                    'icon': 'fa-history',
                    'title': '%d productos volvieron a venderse' % revived_count,
                    'description': 'Items que no se vendían hace más de 1 año tuvieron movimiento',
                    'metric': '%d SKUs' % revived_count,
                    'category_id': None,
                    '_priority': min(revived_count * 5, 50),
                })

        # Ordenar por prioridad descendente y limitar
        insights.sort(key=lambda x: x.get('_priority', 0), reverse=True)
        for ins in insights:
            ins.pop('_priority', None)

        return {
            'period': {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()},
            'prev_period': {'date_from': prev_from.isoformat(), 'date_to': prev_to.isoformat()},
            'insights': insights[:8],
        }

    # =====================================================================
    # Stock Muerto / Inmovilizado
    # =====================================================================
    @api.model
    def get_stock_dead_inventory(self, filters=None):
        """
        Identifica productos con stock disponible que NO rotaron bien en el período.

        Para cada producto con qty_available > 0 devuelve:
          - qty_available (suma sobre ubicaciones internas via stock_quant)
          - value_in_stock = qty_available * standard_price (capital inmovilizado)
          - antiquity_days (desde primera recepción)
          - last_sale_date / days_since_last_sale (en CUALQUIER fecha)
          - qty_sold_in_period / revenue_in_period
          - months_of_stock (qty_available / tasa mensual de ventas del período)
          - classification:
              * 'no_movement': qty vendida en el período = 0 (stock muerto puro).
              * 'low_rotation': vendió, pero cobertura > 6 meses (sobrestock).
              * 'healthy': cobertura <= 6 meses (rotación aceptable).

        Filtros: preset, date_from, date_to, category_id, company_ids.
        """
        if filters is None:
            filters = {}

        # Selector de compañía: acota el contexto (ORM + SQL crudo). Vacío/ambas = todo.
        # Criterio de valoración: 1 producto = 1 costo. Al juntar compañías la cantidad
        # se suma pero el costo es ÚNICO (el de la compañía de referencia = la menor id,
        # MATRIZ cuando están ambas). No se suman ni promedian costos (no infla el valor).
        company_options = self._company_options()
        selected_company_ids = self._effective_company_ids(filters)
        # env.company = primer elemento de allowed_company_ids en Odoo 18, así que
        # ordenamos ascendente: la compañía de referencia para el costo único es la
        # de menor id (MATRIZ cuando están ambas). Determinístico sin importar la sesión.
        selected_company_ids = sorted(selected_company_ids)
        self = self.with_context(allowed_company_ids=selected_company_ids)

        today = fields.Date.today()

        # Resolución de período (idéntico al endpoint principal)
        preset = (filters.get('preset') or '').lower()
        p_from, p_to = self._resolve_period_preset(preset, today)
        if p_from and p_to:
            date_from = p_from
            date_to = p_to
        else:
            default_to = today.replace(day=1) + relativedelta(months=1, days=-1)
            default_from = today.replace(day=1) - relativedelta(months=5)
            date_from = self._as_date(filters.get('date_from'), default_from)
            date_to = self._as_date(filters.get('date_to'), default_to)

        category_id = int(filters['category_id']) if filters.get('category_id') else None

        company_currency = self.env.company.currency_id
        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }
        empty_summary = {
            'no_movement':  {'count': 0, 'value': 0.0, 'qty_available': 0.0, 'avg_antiquity_days': 0.0},
            'low_rotation': {'count': 0, 'value': 0.0, 'qty_available': 0.0, 'avg_antiquity_days': 0.0},
            'healthy':      {'count': 0, 'value': 0.0, 'qty_available': 0.0, 'avg_antiquity_days': 0.0},
        }

        # Si no hay modulo de stock, no podemos calcular stock fisico
        if 'stock.quant' not in self.env:
            return {
                'currency': currency_info,
                'period': {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()},
                'summary': empty_summary,
                'totals': {'total_value': 0.0, 'total_skus': 0, 'total_qty': 0.0},
                'items': [],
            }

        # 1) Productos con stock fisico > 0 (sumando ubicaciones internas).
        #    Respeta el conmutador de compañías de Odoo (self.env.companies).
        company_ids = self.env.companies.ids or [self.env.company.id]
        self.env.cr.execute('''
            SELECT sq.product_id AS product_id, SUM(sq.quantity) AS qty
            FROM stock_quant sq
            JOIN stock_location sl ON sl.id = sq.location_id
            WHERE sl.usage = 'internal'
              AND sl.company_id IN %s
            GROUP BY sq.product_id
            HAVING SUM(sq.quantity) > 0
        ''', (tuple(company_ids),))
        stock_rows = self.env.cr.dictfetchall()
        stock_map = {r['product_id']: float(r['qty'] or 0.0) for r in stock_rows}
        pids = list(stock_map.keys())

        # VALORIZACIÓN CONTABLE (criterio Odoo Reporting → Valoración): valor real de
        # las capas de valoración (stock.valuation.layer), por producto y compañía.
        # NO es qty × standard_price (eso es una aproximación con el promedio móvil
        # actual); las capas reflejan el costo efectivo de las unidades en stock (AVCO)
        # y concilian con la contabilidad. Por eso difiere del reporte "Existencias".
        value_map = {}
        if pids:
            self.env.cr.execute('''
                SELECT product_id, COALESCE(SUM(value), 0) AS value
                FROM stock_valuation_layer
                WHERE company_id IN %s AND product_id IN %s
                GROUP BY product_id
            ''', (tuple(company_ids), tuple(pids)))
            value_map = {r['product_id']: float(r['value'] or 0.0) for r in self.env.cr.dictfetchall()}

        # Excluir productos ARCHIVADOS (active=False): no son parte del catálogo
        # vigente. Se cuantifica su capital (a costo propio) para la nota de exclusión.
        archived_filter = {'value': 0.0, 'sku_count': 0,
                           'reason': 'Se excluye el stock de productos archivados (active=False).'}
        if pids:
            archived = self.env['product.product'].with_context(active_test=False).search([
                ('id', 'in', pids), ('active', '=', False),
            ])
            if archived:
                arch_ids = set(archived.ids)
                archived_filter['value'] = sum(value_map.get(pid, 0.0) for pid in arch_ids)
                archived_filter['sku_count'] = len(archived)
                pids = [pid for pid in pids if pid not in arch_ids]
                stock_map = {pid: stock_map[pid] for pid in pids}
                value_map = {pid: value_map[pid] for pid in pids}

        if not pids:
            return {
                'currency': currency_info,
                'period': {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()},
                'summary': empty_summary,
                'totals': {'total_value': 0.0, 'total_skus': 0, 'total_qty': 0.0},
                'items': [],
            }

        # Filtro opcional por categoría
        if category_id:
            filtered_prods = self.env['product.product'].search([
                ('id', 'in', pids),
                ('categ_id', '=', category_id),
            ])
            pids = filtered_prods.ids
            stock_map = {pid: stock_map[pid] for pid in pids if pid in stock_map}

        if not pids:
            return {
                'currency': currency_info,
                'period': {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()},
                'summary': empty_summary,
                'totals': {'total_value': 0.0, 'total_skus': 0, 'total_qty': 0.0},
                'items': [],
            }

        # 2) Info de producto
        prods = self.env['product.product'].browse(pids)
        prods.read(['name', 'default_code', 'categ_id', 'standard_price'])
        prod_info = {p.id: p for p in prods}

        # 3) Última venta (cualquier fecha, no restringido al período)
        last_sale_map = {}
        self.env.cr.execute('''
            SELECT aml.product_id, MAX(am.invoice_date) AS last_sold
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE am.state = 'posted'
              AND am.move_type = 'out_invoice'
              AND aml.product_id IN %s
            GROUP BY aml.product_id
        ''', (tuple(pids),))
        for row in self.env.cr.dictfetchall():
            ls = row['last_sold']
            if isinstance(ls, str):
                ls = fields.Date.from_string(ls)
            if ls:
                last_sale_map[row['product_id']] = ls

        # 4) Primera recepción (para antigüedad)
        first_reception_map = {}
        if 'stock.move' in self.env:
            try:
                self.env.cr.execute('''
                    SELECT sm.product_id, MIN(sm.date)::date AS first_recv
                    FROM stock_move sm
                    JOIN stock_location sl ON sl.id = sm.location_id
                    WHERE sm.state = 'done'
                      AND sl.usage = 'supplier'
                      AND sm.product_id IN %s
                    GROUP BY sm.product_id
                ''', (tuple(pids),))
                for row in self.env.cr.dictfetchall():
                    fr = row['first_recv']
                    if isinstance(fr, str):
                        fr = fields.Date.from_string(fr)
                    if fr:
                        first_reception_map[row['product_id']] = fr
            except Exception:
                pass

        # 5) Ventas en el período (qty y revenue)
        period_inv_dom = [
            ('parent_state', '=', 'posted'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to),
            ('display_type', '=', 'product'),
            ('product_id', 'in', pids),
            ('move_id.move_type', '=', 'out_invoice'),
        ]
        period_ref_dom = list(period_inv_dom)
        period_ref_dom[-1] = ('move_id.move_type', '=', 'out_refund')

        inv_g = self.env['account.move.line'].read_group(
            period_inv_dom, ['product_id', 'price_total:sum', 'quantity:sum'], ['product_id'])
        ref_g = self.env['account.move.line'].read_group(
            period_ref_dom, ['product_id', 'price_total:sum', 'quantity:sum'], ['product_id'])
        period_rev = self._signed_sum(inv_g, ref_g, 'product_id', 'price_total')
        period_qty = self._signed_sum(inv_g, ref_g, 'product_id', 'quantity')

        # 6) Armar items + clasificación
        period_days = max((date_to - date_from).days + 1, 1)
        period_months = max(period_days / 30.0, 0.1)
        LOW_ROTATION_THRESHOLD = 6.0  # >6 meses de cobertura = baja rotación

        items = []
        for pid in pids:
            product = prod_info.get(pid)
            if not product:
                continue
            qty_avail = stock_map.get(pid, 0.0)
            if qty_avail <= 0:
                continue
            std_price = product.standard_price or 0.0
            # Valor a costo de cada compañía (criterio Odoo nativo multi-empresa).
            value_in_stock = value_map.get(pid, std_price * qty_avail)

            fr = first_reception_map.get(pid)
            antiquity_days = max((today - fr).days, 0) if fr else 0

            ls = last_sale_map.get(pid)
            days_since_last_sale = (today - ls).days if ls else None

            qty_sold = period_qty.get(pid, 0.0)
            revenue = period_rev.get(pid, 0.0)

            if qty_sold <= 0:
                classification = 'no_movement'
                months_of_stock = None
            else:
                monthly_rate = qty_sold / period_months
                months_of_stock = (qty_avail / monthly_rate) if monthly_rate > 0 else None
                if months_of_stock is not None and months_of_stock > LOW_ROTATION_THRESHOLD:
                    classification = 'low_rotation'
                else:
                    classification = 'healthy'

            items.append({
                'id': pid,
                'name': product.name or '',
                'code': product.default_code or '',
                'category': (product.categ_id.name if product.categ_id else ''),
                'category_id': product.categ_id.id if product.categ_id else 0,
                'qty_available': qty_avail,
                'standard_price': std_price,
                'value_in_stock': value_in_stock,
                'antiquity_days': antiquity_days,
                'first_reception_date': fr.isoformat() if fr else '',
                'last_sale_date': ls.isoformat() if ls else '',
                'days_since_last_sale': days_since_last_sale,
                'qty_sold_in_period': qty_sold,
                'revenue_in_period': revenue,
                'months_of_stock': months_of_stock,
                'classification': classification,
            })

        # 7) Resumen por clasificación
        summary = {
            'no_movement':  {'count': 0, 'value': 0.0, 'qty_available': 0.0, '_ant_sum': 0.0},
            'low_rotation': {'count': 0, 'value': 0.0, 'qty_available': 0.0, '_ant_sum': 0.0},
            'healthy':      {'count': 0, 'value': 0.0, 'qty_available': 0.0, '_ant_sum': 0.0},
        }
        for it in items:
            cls = it['classification']
            summary[cls]['count'] += 1
            summary[cls]['value'] += it['value_in_stock']
            summary[cls]['qty_available'] += it['qty_available']
            summary[cls]['_ant_sum'] += it['antiquity_days'] or 0
        for cls, b in summary.items():
            b['avg_antiquity_days'] = (b['_ant_sum'] / b['count']) if b['count'] > 0 else 0.0
            b.pop('_ant_sum', None)

        # Orden default: capital inmovilizado descendente
        items.sort(key=lambda x: x['value_in_stock'], reverse=True)

        return {
            'currency': currency_info,
            'period': {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()},
            'summary': summary,
            'totals': {
                'total_value': sum(it['value_in_stock'] for it in items),
                'total_skus': len(items),
                'total_qty': sum(it['qty_available'] for it in items),
            },
            'thresholds': {
                'low_rotation_months': LOW_ROTATION_THRESHOLD,
            },
            # Nota: capital de productos archivados excluido del cálculo.
            'archived_filter': archived_filter,
            # Selector de compañía: opciones disponibles + selección efectiva.
            'companies': company_options,
            'selected_company_ids': selected_company_ids,
            'items': items[:500],  # cap para no enviar miles de filas al frontend
        }

    # =====================================================================
    # Desglose semanal de un mes (4 semanas: 1-7, 8-14, 15-21, 22-fin)
    # =====================================================================
    @api.model
    def get_product_weekly_breakdown(self, filters=None):
        """
        Devuelve el desglose semanal (4 semanas) de un mes determinado, usando
        la misma logica de Top 8 productos + Otros del dashboard mensual.

        Parametros (filters):
          - month_start (YYYY-MM-DD) y month_end (YYYY-MM-DD): rango del mes.
          - category_id, product_ids, antiquity: mismos filtros del dashboard.

        Si no se reciben month_start/month_end, usa el mes actual.
        """
        if filters is None:
            filters = {}

        today = fields.Date.today()
        # Mes por defecto: el actual
        default_start = today.replace(day=1)
        default_end = (default_start + relativedelta(months=1, days=-1))
        m_start = self._as_date(filters.get('month_start'), default_start)
        m_end = self._as_date(filters.get('month_end'), default_end)

        # Cap m_end al ultimo dia del mes de m_start para evitar rangos raros
        last_day_of_month = m_start + relativedelta(months=1, days=-1)
        if m_end > last_day_of_month:
            m_end = last_day_of_month

        category_id = int(filters['category_id']) if filters.get('category_id') else None
        product_ids = filters.get('product_ids') or []
        try:
            product_ids = [int(x) for x in product_ids if x]
        except Exception:
            product_ids = []
        antiquity_bucket = (filters.get('antiquity') or 'all').lower()
        group_by = (filters.get('group_by') or 'product').lower()
        if group_by not in ('product', 'category'):
            group_by = 'product'

        try:
            top_n = int(filters.get('top_n') or 8)
        except Exception:
            top_n = 8
        if top_n not in (8, 15, 25):
            top_n = 8

        company_currency = self.env.company.currency_id

        # Dominio base del MES completo
        base_line_domain = [
            ('parent_state', '=', 'posted'),
            ('move_id.invoice_date', '>=', m_start),
            ('move_id.invoice_date', '<=', m_end),
            ('display_type', '=', 'product'),
        ]
        if category_id:
            base_line_domain.append(('product_id.categ_id', '=', category_id))
        if product_ids:
            base_line_domain.append(('product_id', 'in', product_ids))

        inv_line_dom = base_line_domain + [('move_id.move_type', '=', 'out_invoice')]
        ref_line_dom = base_line_domain + [('move_id.move_type', '=', 'out_refund')]

        # Top productos del mes (para determinar Top 8 + Otros)
        inv_prod_g = self.env['account.move.line'].read_group(
            inv_line_dom,
            ['product_id', 'price_total:sum', 'quantity:sum'],
            ['product_id'])
        ref_prod_g = self.env['account.move.line'].read_group(
            ref_line_dom,
            ['product_id', 'price_total:sum', 'quantity:sum'],
            ['product_id'])
        prod_rev = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', 'price_total')
        prod_qty = self._signed_sum(inv_prod_g, ref_prod_g, 'product_id', 'quantity')

        all_pids = list(set(list(prod_rev.keys()) + list(prod_qty.keys())))

        # Antiguedad por producto
        first_reception_map = {}
        if all_pids and 'stock.move' in self.env:
            try:
                self.env.cr.execute('''
                    SELECT sm.product_id, MIN(sm.date)::date AS first_recv
                    FROM stock_move sm
                    JOIN stock_location sl ON sl.id = sm.location_id
                    WHERE sm.state = 'done'
                      AND sl.usage = 'supplier'
                      AND sm.product_id IN %s
                    GROUP BY sm.product_id
                ''', (tuple(all_pids),))
                for row in self.env.cr.dictfetchall():
                    fr = row['first_recv']
                    if isinstance(fr, str):
                        fr = fields.Date.from_string(fr)
                    if fr:
                        first_reception_map[row['product_id']] = fr
            except Exception:
                first_reception_map = {}

        prods = self.env['product.product'].browse(all_pids)
        if prods:
            prods.read(['name', 'default_code', 'create_date'])
        prod_info = {p.id: p for p in prods}

        def _antiquity(pid):
            product = prod_info.get(pid)
            fr = first_reception_map.get(pid)
            if fr:
                return max((today - fr).days, 0), 'reception'
            if product and product.create_date:
                cd = product.create_date
                if isinstance(cd, datetime.datetime):
                    cd = cd.date()
                return max((today - cd).days, 0), 'created'
            return 0, 'unknown'

        def in_bucket(days):
            if antiquity_bucket == 'lt90':
                return days < 90
            if antiquity_bucket == '90_365':
                return 90 <= days < 365
            if antiquity_bucket == 'gt365':
                return days >= 365
            return True

        antiquity_map = {}
        filtered_pids = []
        for pid in all_pids:
            d, src = _antiquity(pid)
            antiquity_map[pid] = {'days': d, 'source': src}
            if in_bucket(d):
                filtered_pids.append(pid)

        ranking_by_rev = sorted(
            [(pid, prod_rev.get(pid, 0.0)) for pid in filtered_pids],
            key=lambda x: x[1], reverse=True
        )
        TOP_N = top_n
        top_pids = [pid for pid, _ in ranking_by_rev[:TOP_N]]
        top_pid_set = set(top_pids)

        # Map producto -> categoria (modo group_by='category')
        prod_to_cat = {}
        cat_names = {}
        for pid in all_pids:
            product = prod_info.get(pid)
            if not product:
                continue
            cat = product.categ_id
            if cat and cat.id:
                prod_to_cat[pid] = cat.id
                cat_names[cat.id] = cat.name or 'Sin Categoría'
            else:
                prod_to_cat[pid] = 0
                cat_names[0] = 'Sin Categoría'

        cat_rev_total = {}
        for pid in filtered_pids:
            cid = prod_to_cat.get(pid, 0)
            cat_rev_total[cid] = cat_rev_total.get(cid, 0.0) + prod_rev.get(pid, 0.0)
        sorted_cats = sorted(cat_rev_total.items(), key=lambda x: x[1], reverse=True)
        top_cat_ids = [cid for cid, _ in sorted_cats[:TOP_N]]
        top_cat_set = set(top_cat_ids)

        # ---- 4 buckets de semanas: dias 1-7, 8-14, 15-21, 22-fin de mes ----
        eom = m_start + relativedelta(months=1, days=-1)
        week_buckets = []
        starts = [1, 8, 15, 22]
        for i, ds in enumerate(starts):
            de = starts[i + 1] - 1 if i + 1 < len(starts) else eom.day
            w_start = m_start.replace(day=ds)
            w_end = m_start.replace(day=de)
            week_buckets.append((w_start, w_end))

        weeks_labels = [f"S{i+1} ({b[0].day}-{b[1].day})" for i, b in enumerate(week_buckets)]
        weeks_ranges = [{'start': b[0].isoformat(), 'end': b[1].isoformat()} for b in week_buckets]

        if group_by == 'category':
            series = {cid: [0.0] * len(week_buckets) for cid in top_cat_ids}
        else:
            series = {pid: [0.0] * len(week_buckets) for pid in top_pids}
        others_series = [0.0] * len(week_buckets)
        total_per_week = [0.0] * len(week_buckets)

        for idx, (w_start, w_end) in enumerate(week_buckets):
            w_inv_dom = list(base_line_domain) + [
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.invoice_date', '>=', w_start),
                ('move_id.invoice_date', '<=', w_end),
            ]
            w_ref_dom = list(base_line_domain) + [
                ('move_id.move_type', '=', 'out_refund'),
                ('move_id.invoice_date', '>=', w_start),
                ('move_id.invoice_date', '<=', w_end),
            ]
            w_inv_g = self.env['account.move.line'].read_group(
                w_inv_dom, ['product_id', 'price_total:sum'], ['product_id'])
            w_ref_g = self.env['account.move.line'].read_group(
                w_ref_dom, ['product_id', 'price_total:sum'], ['product_id'])
            w_rev = self._signed_sum(w_inv_g, w_ref_g, 'product_id', 'price_total')

            for pid, val in w_rev.items():
                if antiquity_bucket != 'all' and not in_bucket(antiquity_map.get(pid, {}).get('days', 0)):
                    continue
                total_per_week[idx] += val
                if group_by == 'category':
                    cid = prod_to_cat.get(pid, 0)
                    if cid in top_cat_set:
                        series[cid][idx] += val
                    else:
                        others_series[idx] += val
                else:
                    if pid in top_pid_set:
                        series[pid][idx] += val
                    else:
                        others_series[idx] += val

        datasets = []
        if group_by == 'category':
            for cid in top_cat_ids:
                datasets.append({
                    '_kind': 'category',
                    'category_id': cid,
                    'product_id': 0,
                    'name': cat_names.get(cid, 'Sin Categoría'),
                    'code': '',
                    'data': series[cid],
                    'antiquity_days': None,
                    'antiquity_source': None,
                })
            datasets.append({
                '_kind': 'category',
                'category_id': 0,
                'product_id': 0,
                'name': 'Otros',
                'code': '',
                'data': others_series,
                'antiquity_days': None,
                'antiquity_source': 'others',
            })
        else:
            for pid, _rev in ranking_by_rev[:TOP_N]:
                product = prod_info.get(pid)
                datasets.append({
                    '_kind': 'product',
                    'product_id': pid,
                    'category_id': 0,
                    'name': (product.name if product else '') or '',
                    'code': (product.default_code if product else '') or '',
                    'data': series[pid],
                    'antiquity_days': antiquity_map.get(pid, {}).get('days'),
                    'antiquity_source': antiquity_map.get(pid, {}).get('source'),
                })
            datasets.append({
                '_kind': 'product',
                'product_id': 0,
                'category_id': 0,
                'name': 'Otros',
                'code': '',
                'data': others_series,
                'antiquity_days': None,
                'antiquity_source': 'others',
            })

        currency_info = {
            'symbol': company_currency.symbol or '',
            'name': company_currency.name or '',
            'position': company_currency.position or 'before',
            'decimal_places': (company_currency.decimal_places
                               if company_currency.decimal_places is not None else 2),
        }

        return {
            'currency': currency_info,
            'month': {
                'start': m_start.isoformat(),
                'end': m_end.isoformat(),
                'label': m_start.strftime('%b/%y'),
            },
            'weeks': {
                'labels': weeks_labels,
                'ranges': weeks_ranges,
                'total_per_week': total_per_week,
            },
            'weekly_stack': {
                'datasets': datasets,
                'group_by': group_by,
                'top_n': TOP_N,
                'top_product_ids': list(top_pid_set),
                'top_category_ids': list(top_cat_set),
            },
        }
