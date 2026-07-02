# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPackingList(models.Model):
    _name = 'stock.packing.list'
    _description = 'Packing List de Exportacion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Numero',
        required=True, copy=False, readonly=True, index=True,
        default=lambda self: _('Nuevo'), tracking=True,
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking', string='Nota de Remision',
        required=True, ondelete='restrict', tracking=True,
    )
    sale_id = fields.Many2one(
        comodel_name='sale.order', string='Orden de Venta',
        related='picking_id.sale_id', store=True, readonly=True,
    )
    invoice_id = fields.Many2one(
        comodel_name='account.move', string='Factura de Exportacion',
        domain="[('move_type', 'in', ('out_invoice', 'out_refund')), "
               "('partner_id', '=', consignee_partner_id)]",
        tracking=True,
    )
    date = fields.Date(
        string='Fecha', default=fields.Date.context_today,
        required=True, tracking=True,
    )
    state = fields.Selection(
        selection=[('draft', 'Borrador'), ('confirmed', 'Confirmado'), ('cancelled', 'Cancelado')],
        string='Estado', default='draft', required=True, copy=False, tracking=True,
    )

    incoterm_id = fields.Many2one(comodel_name='account.incoterms', string='Incoterm')
    transport_mode = fields.Selection(
        selection=[('air', 'Aereo'), ('sea', 'Maritimo'), ('road', 'Terrestre / Carretera'), ('rail', 'Ferroviario')],
        string='Modo de Transporte', default='road',
    )
    port_origin = fields.Char(string='Puerto / Aeropuerto de Salida')
    port_destination = fields.Char(string='Puerto / Aeropuerto de Llegada')
    country_origin_id = fields.Many2one(
        comodel_name='res.country', string='Pais de Origen',
        default=lambda self: self._default_country_origin(),
    )
    country_dest_id = fields.Many2one(comodel_name='res.country', string='Pais de Destino')
    consignee_partner_id = fields.Many2one(
        comodel_name='res.partner', string='Consignatario', tracking=True,
    )
    shipper_partner_id = fields.Many2one(
        comodel_name='res.partner', string='Exportador / Shipper',
        default=lambda self: self.env.company.partner_id,
    )

    # Bultos (BOX / CAJAS) - cada bulto puede tener varias lineas adentro
    package_ids = fields.One2many(
        comodel_name='stock.packing.list.package',
        inverse_name='packing_list_id',
        string='Bultos / BOXES', copy=True,
    )
    # Acceso plano a todas las lineas (para reportes/queries)
    package_line_ids = fields.One2many(
        comodel_name='stock.packing.list.line',
        inverse_name='packing_list_id',
        string='Todas las Lineas', readonly=True,
    )

    notes = fields.Text(string='Observaciones')

    # Campos especificos Paraguay
    dua_number = fields.Char(string='Nro DUA', help='Numero de Declaracion Unica Aduanera (opcional).')
    eremision_number = fields.Char(
        string='Nro e-Remision SIFEN',
        compute='_compute_eremision_number', store=True, readonly=False,
    )
    seal_number = fields.Char(string='Nro Precinto / Marchamo')

    # Totales computados
    total_packages = fields.Integer(string='Total Bultos', compute='_compute_totals', store=True)
    total_lines = fields.Integer(string='Total Lineas', compute='_compute_totals', store=True)
    total_quantity = fields.Float(
        string='Cant. Total Productos', digits='Product Unit of Measure',
        compute='_compute_totals', store=True,
    )
    total_net_weight = fields.Float(string='Peso Neto Total (kg)', compute='_compute_totals', store=True, digits=(16, 3))
    total_gross_weight = fields.Float(string='Peso Bruto Total (kg)', compute='_compute_totals', store=True, digits=(16, 3))
    total_volume = fields.Float(string='Volumen Total (m3)', compute='_compute_totals', store=True, digits=(16, 4))

    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Compania',
        required=True, default=lambda self: self.env.company,
    )

    # Configuracion de impresion
    hide_commercial_section = fields.Boolean(
        string='Ocultar Datos Comerciales en PDF', default=False,
    )
    hide_logistics_section = fields.Boolean(
        string='Ocultar Datos Logisticos en PDF', default=False,
    )

    @api.model
    def _default_country_origin(self):
        company = self.env.company
        if company.country_id:
            return company.country_id.id
        py = self.env.ref('base.py', raise_if_not_found=False)
        return py.id if py else False

    @api.depends('package_ids', 'package_ids.net_weight', 'package_ids.gross_weight',
                 'package_ids.volume', 'package_ids.total_quantity', 'package_ids.line_count')
    def _compute_totals(self):
        for rec in self:
            pkgs = rec.package_ids
            rec.total_packages = len(pkgs)
            rec.total_lines = sum(pkgs.mapped('line_count'))
            rec.total_quantity = sum(pkgs.mapped('total_quantity'))
            rec.total_net_weight = sum(pkgs.mapped('net_weight'))
            rec.total_gross_weight = sum(pkgs.mapped('gross_weight'))
            rec.total_volume = sum(pkgs.mapped('volume'))

    @api.depends('picking_id')
    def _compute_eremision_number(self):
        for rec in self:
            value = False
            picking = rec.picking_id
            if picking:
                for fname in ('l10n_py_einvoice_number', 'l10n_py_edoc_number',
                              'sifen_cdc', 'l10n_py_cdc', 'cdc'):
                    if fname in picking._fields and picking[fname]:
                        value = picking[fname]
                        break
                if not value:
                    value = picking.name
            rec.eremision_number = value

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            partner = self.picking_id.partner_id
            self.consignee_partner_id = partner.id if partner else False
            if partner and partner.country_id:
                self.country_dest_id = partner.country_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                seq = self.env['ir.sequence'].next_by_code('stock.packing.list')
                vals['name'] = seq or _('Nuevo')
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('No se puede eliminar un Packing List confirmado. Cancelelo primero.'))
        return super().unlink()

    def action_confirm(self):
        for rec in self:
            if not rec.package_ids:
                raise UserError(_('No se puede confirmar un Packing List sin bultos.'))
            for pkg in rec.package_ids:
                if not pkg.line_ids:
                    raise UserError(_('El bulto "%s" no tiene lineas.') % pkg.name)
            rec.state = 'confirmed'
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
        return True

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
        return True

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'l10n_py_export_packinglist_cross.action_report_packinglist'
        ).report_action(self)
