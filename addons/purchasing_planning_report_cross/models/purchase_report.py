from odoo import models, fields, tools, api
import logging

_logger = logging.getLogger(__name__)

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    report_partner_id = fields.Many2one(
        'res.partner', 
        related='order_id.partner_id', 
        string='Cliente (Reporte)',
        store=False,
        readonly=True
    )

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ReportPurchaseFinal(models.Model):
    _name = 'report.purchase.data.consolidated'
    _description = 'Consolidated Purchase Report Data'
    _auto = True 
    _order = 'default_code, name'

    name = fields.Char(string='Descripción', readonly=True)
    default_code = fields.Char(string='Referencia', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    categ_id = fields.Many2one('product.category', string='Categoría de producto', readonly=True)
    qty_purchased = fields.Float(string='Comprados', readonly=True)
    qty_sold = fields.Float(string='Vendidos', readonly=True)
    qty_available = fields.Float(string='Stock Actual', readonly=True)
    amount_purchased = fields.Monetary(string='Valor compra', readonly=True, currency_field='currency_id')
    amount_sold = fields.Monetary(string='Valor venta', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', compute='_compute_currency')
    date_from = fields.Date(string='Desde', readonly=True)
    date_to = fields.Date(string='Hasta', readonly=True)
    last_vendor_id = fields.Many2one('res.partner', string='Último Proveedor', readonly=True)

    def _compute_currency(self):
        currency = self.env.company.currency_id
        for rec in self:
            rec.currency_id = currency

    # ---- Computed Sub-views ----
    purchase_line_ids = fields.Many2many(
        'purchase.order.line', 
        'report_purchase_data_purch_rel', 
        'report_id', 'line_id',
        compute='_compute_order_lines', 
        string='Productos Comprados'
    )
    sale_line_ids = fields.Many2many(
        'sale.order.line', 
        'report_purchase_data_sale_rel', 
        'report_id', 'line_id',
        compute='_compute_order_lines', 
        string='Productos Vendidos'
    )
    pos_line_ids = fields.Many2many(
        'pos.order.line', 
        'report_purchase_data_pos_rel', 
        'report_id', 'line_id',
        compute='_compute_order_lines', 
        string='Ventas PDV'
    )

    def _compute_order_lines(self):
        for rec in self:
            if not rec.product_id:
                rec.purchase_line_ids = False
                rec.sale_line_ids = False
                rec.pos_line_ids = False
                continue
            
            # Build date domain from the stored range on this record
            date_domain_purchase = [('order_id.date_approve', '>=', rec.date_from), ('order_id.date_approve', '<=', rec.date_to)] if rec.date_from and rec.date_to else []
            date_domain_sale = [('order_id.date_order', '>=', str(rec.date_from)), ('order_id.date_order', '<=', str(rec.date_to) + ' 23:59:59')] if rec.date_from and rec.date_to else []
            date_domain_pos = [('create_date', '>=', str(rec.date_from)), ('create_date', '<=', str(rec.date_to) + ' 23:59:59')] if rec.date_from and rec.date_to else []

            rec.purchase_line_ids = self.env['purchase.order.line'].search([
                ('product_id', '=', rec.product_id.id),
                ('state', 'in', ['purchase', 'done'])
            ] + date_domain_purchase)
            rec.sale_line_ids = self.env['sale.order.line'].search([
                ('product_id', '=', rec.product_id.id),
                ('state', 'in', ['sale', 'done'])
            ] + date_domain_sale)
            rec.pos_line_ids = self.env['pos.order.line'].search([
                ('product_id', '=', rec.product_id.id),
                ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
            ] + date_domain_pos)

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, **kwargs):
        """Auto-populate if empty when the view is loaded"""
        if not self.search_count([]):
            self.action_refresh_report()
        return super().web_search_read(domain=domain, specification=specification, offset=offset, limit=limit, order=order, **kwargs)

    def action_refresh_report(self, date_from=None, date_to=None):
        """Populate the table. Accepts optional date range."""
        from datetime import date as dt_date, timedelta
        if not date_from:
            date_from = dt_date.today() - timedelta(days=90)
        if not date_to:
            date_to = dt_date.today()

        self.env.cr.execute("DELETE FROM report_purchase_data_consolidated")
        
        query = """
            INSERT INTO report_purchase_data_consolidated (create_uid, create_date, write_uid, write_date, name, default_code, product_id, categ_id, qty_purchased, amount_purchased, qty_sold, amount_sold, qty_available, date_from, date_to, last_vendor_id)
            WITH purchase_data AS (
                SELECT 
                    pol.product_id,
                    SUM(pol.product_qty) as qty,
                    SUM(pol.price_total / COALESCE((
                        SELECT r.rate FROM res_currency_rate r 
                        WHERE r.currency_id = po.currency_id 
                          AND r.name <= po.date_approve::date 
                          AND r.company_id = po.company_id
                        ORDER BY r.name DESC LIMIT 1
                    ), 1.0)) as amount
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                WHERE po.state IN ('purchase', 'done')
                  AND po.date_approve::date BETWEEN %s AND %s
                GROUP BY pol.product_id
            ),
            sold_data AS (
                SELECT 
                    sm.product_id,
                    SUM(CASE 
                        WHEN sl_src.usage = 'internal' AND sl_dest.usage = 'customer' THEN sm.product_uom_qty 
                        WHEN sl_src.usage = 'customer' AND sl_dest.usage = 'internal' THEN -sm.product_uom_qty 
                        ELSE 0 END) as qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                WHERE sm.state = 'done'
                  AND sm.date::date BETWEEN %s AND %s
                GROUP BY sm.product_id
            ),
            sale_value_data AS (
                SELECT 
                    sol.product_id,
                    SUM(sol.price_total / COALESCE((
                        SELECT r.rate FROM res_currency_rate r 
                        WHERE r.currency_id = so.currency_id 
                          AND r.name <= so.date_order::date 
                          AND r.company_id = so.company_id
                        ORDER BY r.name DESC LIMIT 1
                    ), 1.0)) as amount
                FROM sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                WHERE so.state IN ('sale', 'done')
                  AND so.date_order::date BETWEEN %s AND %s
                GROUP BY sol.product_id
            ),
            pos_value_data AS (
                SELECT 
                    pol.product_id,
                    SUM(pol.price_subtotal_incl / COALESCE((
                        SELECT r.rate FROM res_currency_rate r 
                        WHERE r.currency_id = COALESCE(aj.currency_id, (SELECT currency_id FROM res_company WHERE id = po.company_id))
                          AND r.name <= po.date_order::date 
                          AND r.company_id = po.company_id
                        ORDER BY r.name DESC LIMIT 1
                    ), 1.0)) as amount
                FROM pos_order_line pol
                JOIN pos_order po ON pol.order_id = po.id
                JOIN pos_session ps ON po.session_id = ps.id
                JOIN pos_config pc ON ps.config_id = pc.id
                JOIN account_journal aj ON pc.journal_id = aj.id
                WHERE po.state IN ('paid', 'done', 'invoiced')
                  AND po.date_order::date BETWEEN %s AND %s
                GROUP BY pol.product_id
            ),
            stock_data AS (
                -- Current stock: always at today's date, not filtered by range
                SELECT
                    sq.product_id,
                    SUM(sq.quantity) AS qty
                FROM stock_quant sq
                JOIN stock_location sl ON sq.location_id = sl.id
                WHERE sl.usage = 'internal'
                GROUP BY sq.product_id
            ),
            last_vendor_data AS (
                -- Get the vendor from the most recent purchase ever (not restricted by range for historical context)
                SELECT DISTINCT ON (pol.product_id)
                    pol.product_id,
                    po.partner_id
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                WHERE po.state IN ('purchase', 'done')
                ORDER BY pol.product_id, po.date_approve DESC, po.id DESC
            )
            SELECT
                %s, CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP,
                COALESCE(
                    t.name->>'es_AR', 
                    t.name->>'en_US', 
                    CASE WHEN jsonb_typeof(t.name) = 'string' THEN t.name->>0 ELSE NULL END,
                    'Producto sin nombre'
                ) as name,
                p.default_code,
                p.id as product_id,
                t.categ_id as categ_id,
                COALESCE(pd.qty, 0) as qty_purchased,
                COALESCE(pd.amount, 0) as amount_purchased,
                COALESCE(sd_sold.qty, 0) as qty_sold,
                COALESCE(svd.amount, 0) + COALESCE(pvd.amount, 0) as amount_sold,
                COALESCE(sd_stock.qty, 0) as qty_available,
                %s as date_from,
                %s as date_to,
                lvd.partner_id
            FROM
                product_product p
                JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN purchase_data pd ON p.id = pd.product_id
                LEFT JOIN sold_data sd_sold ON p.id = sd_sold.product_id
                LEFT JOIN sale_value_data svd ON p.id = svd.product_id
                LEFT JOIN pos_value_data pvd ON p.id = pvd.product_id
                LEFT JOIN stock_data sd_stock ON p.id = sd_stock.product_id
                LEFT JOIN last_vendor_data lvd ON p.id = lvd.product_id
            WHERE
                t.type IN ('consu', 'product')
                AND t.active = true
                AND (pd.qty > 0 OR sd_sold.qty > 0 OR sd_stock.qty > 0)
        """
        self.env.cr.execute(query, (
            date_from, date_to,   # purchase_data filter
            date_from, date_to,   # sold_data filter
            date_from, date_to,   # sale_value_data filter
            date_from, date_to,   # pos_value_data filter
            self.env.user.id, self.env.user.id,  # create_uid, write_uid
            date_from, date_to    # stored date range
        ))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reporte Actualizado',
                'message': 'Los datos de Compras, Ventas y Stock se han sincronizado.',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
