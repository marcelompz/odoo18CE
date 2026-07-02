# -*- coding: utf-8 -*-
"""
Created on 2025-07-29 11:37:42

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AdvancedReceiptPayments(models.Model):
    _name = 'advanced.receipt.payments'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utils.common.mixin.cross']
    _description = 'Recibos de dinero'

    name = fields.Char(
        string='Número', copy=False, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Compañía', default=lambda self: self.env.company, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', tracking=True)
    payment_date = fields.Date(
        string='Fecha', copy=False, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', tracking=True, default=lambda self : self.env.company.currency_id)
    total_amount = fields.Monetary(
        string='Total', currency_field='currency_id', compute='_compute_totals_amounts')
    concept = fields.Char(
        string='Concepto de pago', copy=False, tracking=True)
    state = fields.Selection(
        string='Estado', tracking=True, default='draft', copy=False,
        selection=[('draft', 'Borrador'), ('done', 'Confirmado'), ('canceled','Cancelado')])
    
    # Facturas
    invoice_ids = fields.Many2many(
        'account.move',
        'advanced_receipt_payments_account_move_rel',  # nombre de tabla relacional
        'receipt_payment_id',                          # columna que apunta al modelo actual
        'invoice_id',                                  # columna que apunta a account.move
        string='Facturas Relacionadas'
    )
    invoice_total_amount = fields.Monetary(
        string='Total de facturas', compute='_compute_totals_amounts', currency_field='currency_id')
    customer_invoices_domain = fields.Char(
        string="Dominio de Facturas",
        compute='_compute_customer_invoices_domain',
        store=False,
    )
    
    # Pagos
    payment_ids = fields.Many2many(
        'account.payment')
    payment_total_amount = fields.Monetary(
        string='Total de pagos', compute='_compute_totals_amounts', currency_field='currency_id')
    customer_payments_domain = fields.Char(
        string="Dominio de Pagos",
        compute='_compute_customer_payments_domain',
        store=False,
    )

    # Notas de credito
    credit_note_ids = fields.Many2many(
        'account.move',
        'advanced_receipt_payments_credit_note_rel',   # otra tabla relacional distinta
        'receipt_payment_id',                          # misma columna para el modelo actual
        'credit_note_id',                              # columna distinta para account.move
        string='Notas de Crédito Relacionadas'
    )
    credit_note_total_amount = fields.Monetary(
        string='Total de notas de crédito', compute='_compute_totals_amounts', currency_field='currency_id')
    reversed_entries_ids = fields.Many2many(
        'account.move', compute='_compute_has_credit_note')
    has_credit_note = fields.Boolean(
        compute='_compute_has_credit_note')

    @api.depends('invoice_ids', 'payment_ids', 'credit_note_ids')
    def _compute_totals_amounts(self):
        """
        Computa la sumatorias de los montos de las facturas, pagos
        """
        for record in self:
            record.invoice_total_amount = sum(line.amount_total_signed for line in record.invoice_ids)
            record.payment_total_amount = sum(line.amount_company_currency_signed for line in record.payment_ids)
            record.credit_note_total_amount = sum(line.amount_total_signed for line in record.credit_note_ids)
            record.total_amount = record.payment_total_amount

    @api.depends('partner_id')
    def _compute_customer_invoices_domain(self):
        for rec in self:
            if rec.partner_id:
                domain = [
                    ('partner_id', '=', rec.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid','in_payment','paid','partial','reversed','blocked'])
                ]
                # Convertimos el dominio a su representación en cadena de texto
                rec.customer_invoices_domain = str(domain)
            else:
                rec.customer_invoices_domain = "[('id', '=', 0)]"
                rec.invoice_ids = [(5, 0, 0)]  # Limpiamos las facturas si no hay cliente

    @api.depends('partner_id', 'invoice_ids')
    def _compute_customer_payments_domain(self):
        for rec in self:
            if not rec.partner_id or not rec.invoice_ids:
                rec.customer_payments_domain = "[('id', '=', 0)]"
                rec.payment_ids = [(5, 0, 0)]
                continue

            # 1. Encontrar IDs de pagos ya usados en otros recibos (que no estén cancelados)
            #    Asumo que 'receipt_payment_id' es un campo que añadiste a account.payment
            used_payment_ids = self.env['advanced.receipt.payments'].search([
                ('id', '!=', rec.id or rec._origin.id),
                ('state', '!=', 'canceled'),
            ]).payment_ids.ids

            # 2. Construir el dominio
            domain = [
                ('partner_id', 'child_of', rec.partner_id.id), # Usar child_of es más flexible
                ('state', '=', 'paid'), # En Odoo 18, el estado de un pago validado es 'posted'
                ('payment_type', '=', 'inbound'),
                # Excluir los pagos ya usados
                ('id', 'not in', used_payment_ids),
                # Filtrar por pagos conciliados con las facturas seleccionadas
                ('reconciled_invoice_ids', 'in', rec.invoice_ids.ids)
            ]

            rec.customer_payments_domain = str(domain)

    @api.depends('invoice_ids', 'credit_note_ids')
    def _compute_has_credit_note(self):
        for rec in self:
            rec.has_credit_note = False
            rec.reversed_entries_ids = False

            # Filtrar solo NC válidas que estén en el Many2many y no sean parte de recibos no cancelados
            used_credit_notes = self.env['advanced.receipt.payments'].search([
                ('id', '!=', rec.id),
                ('state', '!=', 'canceled'),
                ('credit_note_ids', 'in', rec.credit_note_ids.ids),
            ]).mapped('credit_note_ids')

            # Excluir las que ya están usadas en otros recibos no cancelados
            available_credit_notes = rec.credit_note_ids.filtered(lambda m: m.id not in used_credit_notes.ids)

            if available_credit_notes:
                rec.has_credit_note = True
                rec.reversed_entries_ids = available_credit_notes.ids

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
    
        copy_data = {
            'name': '/',
            'payment_date': self.get_current_datetime('date'),
            'concept': _('PAGO DE FACTURAS'),
        }
        res.update(copy_data)
    
        return res

    @api.model
    def create(self, values):
        res = super().create(values)

        if 'name' not in res or res['name'] == _('/'):
            res['name'] = self.env['ir.sequence'].next_by_code('advanced.receipt.payments') or _('/')
        
        return res

    def write(self, values):
        res = super().write(values)
        
        # Si 'payment_ids' está en los valores y no tiene registros
        if 'payment_ids' in values and not self.payment_ids:
            values['payment_ids'] = False

         # Si 'credit_note_ids' está en los valores y no tiene registros
        if 'credit_note_ids' in values and not self.credit_note_ids:
            values['credit_note_ids'] = False

        return res

    @api.model 
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'total_amount' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    total_amount = 0.0
                    for rec in lines:
                        total_amount += rec.total_amount
                    line['total_amount'] = total_amount

        return res

    def button_cancel(self):
        # Verificamos que si el recibo esta en estado borrador
        if self.state == 'draft':
            self.write({'state': 'canceled'})
            return

        # Cancelamos los pagos y retenciones
        # for payment in self.payment_ids:
        #     if payment.payment_id:
        #         payment.payment_id.action_draft()
        #         payment.payment_id.action_cancel()

        # Desvinculamos los pagos y retenciones del recibo
        for payment in self.payment_ids:
            payment.receipt_payment_id = False

        # # Rompe conciliacion de la NC con la factua
        # for voucher in self.credit_note_ids:
        #     if voucher.move_id:  # Verificamos que está vinculada a una factura original que ha sido revertida.
        #         outstanding = voucher.move_id.invoice_payments_widget.get('content')

        #         if outstanding:  # Aseguramos que el contenido de pagos está disponible
        #             for move in outstanding:  # Recorre el contenido de pagos
        #                 if move.get('move_id') == voucher.credit_note_id.id:  # Verifica si la NC es la actual
        #                     try:
        #                         partial_id = move.get('partial_id')
        #                         if partial_id:
        #                             # Rompemos la conciliación de la NC como pago a la factura original
        #                             voucher.move_id.js_remove_outstanding_partial(partial_id)
        #                         else:
        #                             raise UserError(_('No se encontró el ID parcial para romper la conciliación.'))
        #                     except Exception as e:
        #                         raise UserError(_('Error al intentar romper la conciliación de la nota de crédito como pago: %s') % str(e))
        #         else:
        #             raise UserError(_('No se encontraron pagos realizados con una nota de crédito.'))

        self.write({'state': 'canceled'})

    def button_done(self):
        # Verifica que tiene al menos un tipo de pago, si no tiene instalado el modulo de recibo de dinero con cheque
        if not self.check_installation('advanced_receiptmoney_cheque_cross') and not self.payment_ids:
            raise ValidationError(_('Se debe seleccionar al menos un pago para generar el recibo de dinero!'))

        # Registramos los pagos y retenciones
        for payment in self.payment_ids:    
        #     # Creamos el pago tipo retencion
        #     if payment.payment_type == 'withholdings':
        #         new_payment = self.env['account.payment.register']\
        #             .with_context(active_model='account.move', active_ids=payment.move_id.ids)\
        #             .create({
        #                 'journal_id': payment.journal_id.id,
        #                 'amount': payment.amount,
        #                 'currency_id': payment.currency_id.id,
        #                 'payment_date': payment.date,
        #                 'communication': _('Retención de factura %s' % payment.move_id.invoice_number if self.check_field_exists(self, 'account.move', 'invoice_number') else payment.move_id.name),
        #             })._create_payments()

        #         payment.payment_id = new_payment.id if new_payment else False
                
            if payment.state == 'draft':
                payment.action_post()

            # if not payment.reconciled_invoice_ids:
            #     for invoice in self.invoice_ids:
            #         if invoice.move_id.amount_residual > 0:
            #             invoice.move_id.js_assign_outstanding_line(payment.payment_id.line_ids[1].id)
            # Vinculamos el recibo al pago o retencion
            payment.receipt_payment_id = self.id

        # Añade las notas de crédito como pago a la factura
        # for voucher in self.credit_note_ids:  # Recorre las líneas de las notas de crédito agregadas
        #     if voucher.move_id:     # Verificamos que la NC tenga una factura vinculada
        #         outstanding = voucher.move_id.invoice_outstanding_credits_debits_widget.get('content') if voucher.move_id.invoice_outstanding_credits_debits_widget else False

        #         if outstanding:  # Aseguramos que el contenido de pagos pendientes está disponible
        #             for move in outstanding:  # Recorre el contenido de movimientos pendientes
        #                 if move.get('move_id') == voucher.credit_note_id.id:  # Verifica si la NC es la actual
        #                     try:
        #                         # Añadimos la NC como pago a la factura original
        #                         voucher.move_id.js_assign_outstanding_line(move.get('id'))
        #                     except Exception as e:
        #                         raise UserError(_('Error al asignar la nota de crédito como pago: %s', str(e)))
        #         else:
        #             _logger.info(f'La nota de crédito ya se encuentra vinculada a la factura')
        #             _logger.info(f'No se encontraron créditos o débitos pendientes para la factura revertida.')

        #     else:
        #         raise UserError(_('Debes vincular una factura a la nota de crédito'))
        self.write({'state': 'done'})

    def button_draft(self):
        self.write({'state': 'draft'})

    def date_to_text(self, report_date, lang):
        date ={
            'es_': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio','Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
            'pt_': ['Janero', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho','Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'],
        }

        try:
            month = date.get(f'{lang[:3]}')[report_date.month - 1]

        except:
            month = date.get('es_')[report_date.month - 1]

        day = report_date.day
        year = report_date.year

        return (_(f'{day} de {month} del {year}'))

    def unlink(self):
        for rec in self:
            if rec.state in ['done', 'canceled']:
                raise UserError(_('Debes pasar a borrador para poder eliminar el recibo.'))
        return super().unlink()
    