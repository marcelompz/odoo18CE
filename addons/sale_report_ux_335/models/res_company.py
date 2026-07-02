# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    product_presupuesto_id = fields.Many2one(
        'product.product',
        string='Producto Presupuesto',
        help='Producto usado como linea unica para el total del presupuesto rapido. '
             'Si no se configura, se buscara un producto con nombre "Presupuesto".',
        domain=[('sale_ok', '=', True)],
    )
    report_background_image = fields.Binary(
        string='Imagen de fondo del reporte',
        help='Imagen de fondo A4 que se repite en todas las paginas del presupuesto.',
    )
    report_background_filename = fields.Char(string='Nombre archivo fondo')
    report_intro_html = fields.Html(
        string='Texto introductorio del presupuesto',
        sanitize_style=True,
        help='Contenido HTML que se mostrara en la seccion introductoria del reporte de presupuesto.',
    )
    report_margin_top = fields.Integer(string='Margen superior (px)', default=35)
    report_margin_bottom = fields.Integer(string='Margen inferior (px)', default=35)
    report_margin_left = fields.Integer(string='Margen izquierdo (px)', default=50)
    report_margin_right = fields.Integer(string='Margen derecho (px)', default=50)
