# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PresupuestoConfigWizard(models.TransientModel):
    _name = 'presupuesto.rapido.config'
    _description = 'Configuracion Presupuesto Rapido'

    product_presupuesto_id = fields.Many2one(
        'product.product',
        string='Producto Presupuesto',
        required=False,
        domain=[('sale_ok', '=', True)],
        help='Producto usado como linea unica para el total del presupuesto rapido.',
    )
    report_background_image = fields.Binary(
        string='Imagen de fondo del reporte',
        help='Imagen de fondo A4 que se repite en todas las paginas del presupuesto.',
    )
    report_background_filename = fields.Char(string='Nombre archivo fondo')
    report_intro_html = fields.Html(
        string='Texto introductorio',
        sanitize_style=True,
    )
    report_margin_top = fields.Integer(string='Margen superior (px)', default=35)
    report_margin_bottom = fields.Integer(string='Margen inferior (px)', default=35)
    report_margin_left = fields.Integer(string='Margen izquierdo (px)', default=50)
    report_margin_right = fields.Integer(string='Margen derecho (px)', default=50)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        if 'product_presupuesto_id' in fields_list and company.product_presupuesto_id:
            res['product_presupuesto_id'] = company.product_presupuesto_id.id
        if 'report_background_image' in fields_list and company.report_background_image:
            res['report_background_image'] = company.report_background_image
            res['report_background_filename'] = company.report_background_filename
        if 'report_intro_html' in fields_list:
            res['report_intro_html'] = company.report_intro_html
        for field in ('report_margin_top', 'report_margin_bottom', 'report_margin_left', 'report_margin_right'):
            if field in fields_list:
                res[field] = getattr(company, field)
        return res

    def action_save(self):
        self.ensure_one()
        vals = {
            'product_presupuesto_id': self.product_presupuesto_id.id if self.product_presupuesto_id else False,
            'report_intro_html': self.report_intro_html,
            'report_margin_top': self.report_margin_top,
            'report_margin_bottom': self.report_margin_bottom,
            'report_margin_left': self.report_margin_left,
            'report_margin_right': self.report_margin_right,
        }
        if self.report_background_image:
            vals['report_background_image'] = self.report_background_image
            vals['report_background_filename'] = self.report_background_filename
        elif not self.report_background_image and self.env.company.report_background_image:
            vals['report_background_image'] = False
            vals['report_background_filename'] = False
        self.env.company.sudo().write(vals)

        return {'type': 'ir.actions.act_window_close'}
