from odoo import http, fields
from odoo.http import request
import json
import datetime
from dateutil.relativedelta import relativedelta

class DashboardCrossController(http.Controller):

    @http.route('/api/dashboard_cross/commercial_data', type='json', auth='user')
    def get_commercial_data(self):
        # 1. KPIs Generales
        today = fields.Date.today()
        first_day_month = today.replace(day=1)
        
        # Filtros básicos para Ventas este mes
        sales_domain = [('state', 'in', ['sale', 'done']), ('date_order', '>=', first_day_month)]
        sales = request.env['sale.order'].search(sales_domain)
        
        total_sales = sum(sales.mapped('amount_untaxed'))
        avg_ticket = total_sales / len(sales) if sales else 0
        
        # Pipieline Abierto
        crm_domain = [('type', '=', 'opportunity'), ('active', '=', True)]
        opportunities = request.env['crm.lead'].search(crm_domain)
        open_pipe = sum(opportunities.mapped('expected_revenue'))
        opp_count = len(opportunities)
        
        # Conversión (simplificada: ganadas vs totales creadas recientemente)
        won_opps = request.env['crm.lead'].search_count([('type', '=', 'opportunity'), ('probability', '=', 100), ('active', '=', True)])
        lost_opps = request.env['crm.lead'].search_count([('type', '=', 'opportunity'), ('probability', '=', 0), ('active', '=', False)])
        total_closed = won_opps + lost_opps
        conversion_rate = (won_opps / total_closed * 100) if total_closed > 0 else 0

        # 2. Pipeline Funnel (agrupado por stage_id)
        stages = request.env['crm.stage'].search([])
        funnel_data = []
        for stage in stages:
            opps_in_stage = opportunities.filtered(lambda o: o.stage_id.id == stage.id)
            funnel_data.append({
                'name': stage.name,
                'count': len(opps_in_stage),
                'revenue': sum(opps_in_stage.mapped('expected_revenue'))
            })

        # 3. Top Vendedores (Ventas Facturadas/Confirmadas)
        sales_by_user = {}
        for sale in sales:
            if sale.user_id:
                if sale.user_id.name not in sales_by_user:
                    sales_by_user[sale.user_id.name] = 0
                sales_by_user[sale.user_id.name] += sale.amount_untaxed
                
        top_salespeople = [{'name': k, 'amount': v} for k, v in sales_by_user.items()]
        top_salespeople = sorted(top_salespeople, key=lambda x: x['amount'], reverse=True)[:5] # Top 5

        # 4. Tendencia de Ventas (últimos 6 meses)
        trends_current = []
        months_labels = []
        for i in range(5, -1, -1):
            start = (today - relativedelta(months=i)).replace(day=1)
            end = start + relativedelta(months=1, days=-1)
            domain = [('state', 'in', ['sale', 'done']), ('date_order', '>=', start), ('date_order', '<=', end)]
            month_sales = sum(request.env['sale.order'].search(domain).mapped('amount_untaxed'))
            trends_current.append(month_sales)
            months_labels.append(start.strftime('%b'))

        data = {
            'kpis': {
                'total_sales': total_sales,
                'avg_ticket': avg_ticket,
                'open_pipe': open_pipe,
                'opp_count': opp_count,
                'conversion_rate': conversion_rate,
            },
            'funnel': funnel_data,
            'top_salespeople': top_salespeople,
            'trends': {
                'labels': months_labels,
                'current_year': trends_current,
                'last_year': [0] * len(trends_current) # Simulacion
            }
        }
        
        return data
