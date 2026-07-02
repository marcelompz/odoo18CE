# -*- coding: utf-8 -*-
"""
Created on 2025-08-15 15:27:20

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.One2many(
        'account.payment', 'sale_order_id', string='Anticipos Registrados')
    payment_count = fields.Integer(
        compute='_compute_payment_count', string='Conteo de Pagos')
    payment_status = fields.Char(
        string='Estado de Pago', compute='_compute_payment_status')
    amount_due = fields.Float(
        string='Monto por pagar', compute='_compute_amount_due')
    payment_details = fields.Binary(
        string='Detalles del pago', compute='_compute_payment_details')
    can_continue = fields.Boolean(
        string='Puede continuar?', compute='_compute_can_continue')

    @api.depends('company_id.advance_approval_percentag')
    def _compute_can_continue(self):
        for record in self:
            approval_percentag = record.company_id.advance_approval_percentag
            record.can_continue = (record.amount_total * approval_percentag >= record.amount_due) and len(record.invoice_ids) > 0
    
    @api.depends('invoice_ids')
    def _compute_payment_status(self):
        """ La función calculará el estado de pago de la orden de venta si se 
        crea una factura para la orden de venta correspondiente. El estado del 
        pago será: pagado, no pagado, parcialmente pagado, revertido, etc. """
        for order in self:
            order.payment_status = 'Sin factura'
            posted_invoices = order.invoice_ids.filtered(
                lambda x: x.state == 'posted')
            if not posted_invoices:
                order.payment_status = 'Sin factura'
            else:
                payment_states = posted_invoices.mapped('payment_state')
                status_length = len(payment_states)
                if order.amount_due > 0:
                    if 'partial' in payment_states or 'not_paid' in payment_states:
                        order.payment_status = 'Parcial'
                    elif 'not_paid' in payment_states and status_length == payment_states.count(
                            'not_paid'):
                        order.payment_status = 'No pagada'
                elif order.amount_due <= 0:  # Changed to <= 0 to handle overpayments or credit notes
                    if 'paid' in payment_states and status_length == payment_states.count(
                            'paid'):
                        order.payment_status = 'Pagada'
                    elif 'in_payment' in payment_states and status_length == payment_states.count(
                            'in_payment'):
                        order.payment_status = 'En proceso de pago'
                elif 'reversed' in payment_states and status_length == payment_states.count(
                        'reversed'):
                    order.payment_status = 'Revertido'

    @api.depends('invoice_ids')
    def _compute_amount_due(self):
        """ La función se utiliza para calcular el importe adeudado de la factura y, 
        si se registra el pago, contabilizar las diferencias de tipo de cambio y las 
        notas de crédito. """
        for rec in self:
            total_invoiced = 0
            total_paid = 0
            for invoice in rec.invoice_ids.filtered(lambda x: x.state == 'posted'):
                if invoice.move_type == 'out_invoice':  # Facturas regulares
                    total_invoiced += invoice.amount_total
                    total_paid += invoice.amount_total - invoice.amount_residual
                elif invoice.move_type == 'out_refund':  # Notas de crédito
                    total_invoiced -= invoice.amount_total
                    total_paid -= (invoice.amount_total - invoice.amount_residual)
            rec.amount_due = total_invoiced - total_paid

    @api.depends('invoice_ids')
    def _compute_payment_details(self):
        """ Calcula los detalles de pago de las facturas y agrega a la vista del 
        formulario de pedido de venta. """
        for rec in self:
            payment = []
            rec.payment_details = False
            if rec.invoice_ids:
                for line in rec.invoice_ids:
                    if line.invoice_payments_widget:
                        for pay in line.invoice_payments_widget['content']:
                            payment.append(pay)
                for line in rec.invoice_ids:
                    if line.invoice_payments_widget:
                        payment_line = line.invoice_payments_widget
                        payment_line['content'] = payment
                        rec.payment_details = payment_line
                        break
                    rec.payment_details = False

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for order in self:
            order.payment_count = len(order.payment_ids)

    def action_register_prepayment(self):
        """Abre el wizard para registrar un nuevo pago de anticipo."""
        # self.ensure_one()
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': _('Registrar Anticipo'),
        #     'res_model': 'sale.advance.payment.wizard',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {
        #         'default_sale_order_id': self.id,
        #         'default_amount': self.amount_due if self.amount_due > 0 else self.amount_total,
        #         'default_currency_id': self.currency_id.id,
        #     }
        # }

        self.ensure_one()
        return {
            'name': _('Registrar Anticipo'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_account_payment_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total,
                'default_ref': f"Anticipo de {self.name}",
                'default_sale_order_id': self.id,
            },
        }

    def _process_prepayment(self, payment):
        """Lógica para crear/encontrar factura y conciliar el pago."""
        self.ensure_one()
        
        # 1. Buscar una factura abierta existente
        open_invoice = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.payment_state != 'paid'
        )

        invoice = open_invoice[0] if open_invoice else None

        # 2. Si no hay factura abierta, crear una nueva
        if not invoice:
            if all(inv.state == 'cancel' for inv in self.invoice_ids):
                # Si todas están canceladas, podemos crear una nueva
                invoice = self._create_invoices()[0]
            elif not self.invoice_ids:
                 invoice = self._create_invoices()[0]
            else:
                 raise UserError(_("La orden ya tiene facturas válidas. No se puede crear una nueva para el anticipo."))
            
            # Confirmar la factura recién creada
            invoice.action_post()

        if self.env.company.prepayment_auto_reconcile:
            # Se crea el pago confirmado y se concilia con la factura   
            try:
                new_payment = self.env['account.payment.register']\
                    .with_context(active_model='account.move', 
                    active_ids=invoice.ids)\
                    .create({
                        'journal_id': payment.get('journal_id', False),
                        'amount': payment.get('amount', 0.0),
                        'currency_id': payment.get('currency_id', False),
                        'payment_date': payment.get('date', fields.Date.context_today(self)),
                        'communication': _('Anticipo para %s') % self.name,
                    })._create_payments()   

                new_payment.action_post()

            except Exception as e:
                _logger.error("Error al conciliar el pago: %s", e)
                raise UserError(_("No se pudo conciliar el pago con la factura. Error: %s") % e)

    def action_view_payments(self):
        """Acción del botón inteligente para ver los pagos."""
        self.ensure_one()
        payments = self.payment_ids
        if len(payments) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Anticipo'),
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': payments.id,
                'context': {'create': False}
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Anticipos'),
                'res_model': 'account.payment',
                'view_mode': 'list,form',
                'domain': [('id', 'in', payments.ids)],
                'context': {'create': False}
            }

    def js_remove_outstanding_partial(self, partial_id):
        """ Lo llama el widget 'pago' para eliminar una entrada conciliada de la 
        factura actual.

        :param partial_id: El ID de una entrada parcial existente conciliada con 
        la factura actual. """
        self.ensure_one()
        partial = self.env['account.partial.reconcile'].browse(partial_id)
        return partial.unlink()
