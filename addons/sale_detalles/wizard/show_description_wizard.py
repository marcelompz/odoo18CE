from odoo import models, fields, api

class ShowDescriptionWizard(models.TransientModel):
    _name = 'show.description.wizard'
    _description = 'Wizard para mostrar la descripción general'

    order_id = fields.Many2one('sale.order', string='Orden', readonly=True)
    general_description = fields.Html(string='Descripción General', readonly=True)
    technical_info_html = fields.Html(string='Información Técnica', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get('default_order_id')
        if order_id:
            res['order_id'] = order_id
            order = self.env['sale.order'].browse(order_id)
            res['general_description'] = order.general_description
            # Generar HTML de información técnica
            html = """
            <table style='width:100%; text-align:left;'>
                <tr><th>Pregunta</th><th>Respuesta</th></tr>
            """
            if order.technical_info_ids:
                for line in order.technical_info_ids:
                    html += f"<tr><td>{line.question_id.name or ''}</td><td>{line.answer or ''}</td></tr>"
            else:
                html += "<tr><td colspan='2'>No hay información técnica asociada a esta orden.</td></tr>"
            html += "</table>"
            res['technical_info_html'] = html
        return res 