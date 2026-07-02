from odoo import models, fields, api
from datetime import datetime, timedelta

class SaleOrderCalendarReport(models.AbstractModel):
    _name = 'report.sale_detalles.sale_order_calendar_report'
    _description = 'Reporte de Calendario de Órdenes de Venta'

    @api.model
    def _get_report_values(self, docids=None, data=None):
        """Obtiene los valores para el reporte"""
        if data and 'start_date' in data and 'end_date' in data:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        else:
            # Por defecto, mostrar el mes actual
            today = fields.Date.today()
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Obtener órdenes en el rango de fechas
        orders = self.env['sale.order'].search([
            ('validity_date', '>=', start_date),
            ('validity_date', '<=', end_date),
            ('validity_date', '!=', False)
        ], order='validity_date')

        # Agrupar órdenes por fecha
        orders_by_date = {}
        for order in orders:
            date_key = order.validity_date.strftime('%Y-%m-%d')
            if date_key not in orders_by_date:
                orders_by_date[date_key] = []
            orders_by_date[date_key].append(order)

        # Calcular estadísticas
        today = fields.Date.today()
        overdue_orders = orders.filtered(lambda o: o.validity_date < today)
        pending_orders = orders.filtered(lambda o: o.validity_date >= today)
        
        total_amount = sum(orders.mapped('amount_total'))
        total_products = sum(orders.mapped('total_products_count'))

        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': orders,
            'orders_by_date': orders_by_date,
            'start_date': start_date,
            'end_date': end_date,
            'overdue_orders': overdue_orders,
            'pending_orders': pending_orders,
            'total_amount': total_amount,
            'total_products': total_products,
            'today': today,
        } 