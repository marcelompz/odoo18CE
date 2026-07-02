# -*- coding: utf-8 -*-
"""
Created on 2025-05-14 13:02:16

@author: drojo
"""
# python
from datetime import timedelta, date

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request


class AccountChequePayment(models.Model):
    _name = 'account.cheque.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Pago con cheque de cuenta'

    name = fields.Char(
        string='Nombre', default='New', readonly=1, tracking=True)
    payment_type = fields.Selection(
        string='Tipo de pago', default='receive_money',tracking=True,
        selection=[('receive_money', 'Recibir dinero'), ('send_money', 'Enviar dinero')])
    partner_id = fields.Many2one(
        'res.partner', string='Cliente/Proveedor', tracking=True)
    payment_amount = fields.Monetary(
        string='Importe en moneda de factura', tracking=True, compute='_compute_payment_amount')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, tracking=True)
    reference = fields.Char(
        string='Titular del cheque', tracking=True)
    journal_id = fields.Many2one(
        'account.journal', string="Diario de pagos", domain=[('type', 'in', ['bank','cash'])], required=1,tracking=True)
    cheque_status = fields.Selection(
        string='Estado del cheque', default='draft', tracking=True,
        selection=[('draft','Borrador'),('deposit','Depositado'),('paid','Pagado')])
    payment_date = fields.Date(
        string='Fecha de pago', default=fields.Date.today(), required=1, tracking=True)
    due_date = fields.Date(
        string='Fecha de vencimiento', required=1, tracking=True)
    memo = fields.Char(
        string='Nota', tracking=True)
    agent = fields.Char(
        string='Número de cuenta', tracking=True)
    bank_id = fields.Many2one(
        'res.bank', string='Banco', tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'cheque_attachment_rel', string='Imagen del cheque')
    company_id = fields.Many2one(
        'res.company', string='Compañía', default=lambda self: self.env.company, tracking=True)
    invoice_id = fields.Many2one(
        'account.move', string='Factura', tracking=True)
    state = fields.Selection(
        string='State', selection='_get_state_values', default='draft', tracking=True)
    deposited_debit = fields.Many2one(
        'account.move.line')
    deposited_credit = fields.Many2one(
        'account.move.line')
    invoice_ids = fields.Many2many(
        'account.move')
    account_move_ids = fields.Many2many(
        'account.move', compute='compute_account_moves')
    done_date = fields.Date(
        string='Done date', readonly=True, tracking=True)
    currency_cheque_id = fields.Many2one(
        'res.currency', string="Moneda del cheque", tracking=True)
    payment_cheque_amount = fields.Monetary(
        string="Monto del cheque", tracking=True, currency_field='currency_cheque_id')
    cheque_nro = fields.Char(
        string='Número de cheque')
    cheque_balance = fields.Float(
        string='Saldo del cheque', default=0)
    payment_id = fields.Many2one(
        'account.payment', string='Referencia de sobrepago')
    deposit_move_id = fields.Many2one(
        'account.move', string="Asiento de Depósito", copy=False, readonly=True)

    def _get_state_values(self):
        return [
            ('draft', 'Borrador'), 
            ('registered', 'Registrado'), 
            ('paid', 'Pagado'), 
            ('done', 'Hecho'), 
            ('deposited', 'Depositado'), 
            ('returned', 'Devuelto'),
            ('bounced', 'Rebotó'), 
            ('cancel', 'Cancelado')
        ]

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Sólo puedes eliminar el cheque en estado de borrador.')

        return super().unlink()

    def action_register_check(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        account_move_model = self.env[active_model].browse(active_id)
        
        if account_move_model.move_type not in ('out_invoice','in_invoice'):
            raise UserError('¡Sólo se consideran las facturas de clientes y proveedores!')

        move_list = []
        payment_amount = 0.0
        payment_type = ''

        if len(active_ids) > 0:
            account_moves = self.env[active_model].browse(active_ids)
            partners = account_moves.mapped('partner_id')

            if len(set(partners)) != 1:
                raise UserError('Partners must be same')
            states = account_moves.mapped('state')

            if len(set(states)) != 1 or states[0] != 'posted':
                raise UserError('¡Solo las facturas enviados por correo se consideran para el pago con cheque!')

            for account_move in account_moves:
                if account_move.payment_state != 'paid' and account_move.amount_residual != 0.0:
                    payment_amount = payment_amount + account_move.amount_residual
                    move_list.append(account_move.id)

        if not move_list:
            raise UserError('¡Las facturas seleccionadas ya están pagadas!')

        if account_moves[0].move_type in ('in_invoice'):
            payment_type = 'send_money'
        
        if account_moves[0].move_type in ('out_invoice'):
            payment_type = 'receive_money'

        return {
            'name': 'Pago con cheque',
            'res_model': 'account.cheque.payment',
            'view_mode': 'form',
            'view_id': self.env.ref('cheque_management_cross.account_cheque_payment_wizard').id,
            'context':{
                'default_invoice_ids':[(6,0,move_list)],
                'default_partner_id': account_move_model.partner_id.id,
                'default_payment_amount':payment_amount,
                'default_payment_type': payment_type
            },
            'target': 'new',
            'type': 'ir.actions.act_window'
        }

    def open_attachments(self):
        [action] = self.env.ref('base.action_attachment').read()
        action['domain'] = [('id', 'in', self.attachment_ids.ids)]

        return action

    def open_journal_items(self):
        [action] = self.env.ref('account.action_account_moves_all').read()
        ids = self.env['account.move.line'].search([('cheque_id', '=', self.id)])
        id_list = []

        for cheque_id in ids:
            id_list.append(cheque_id.id)
        
        if id_list:
            action['domain'] = [('id', 'in', id_list)]

        else:
            action['domain'] = [('id', '=', False)]

        return action

    def open_journal_entry(self):
        [action] = self.env.ref('cheque_management_cross.account_cheque_payment_move_journal_line_action').read()
        ids = self.env['account.move'].search([('cheque_id', '=', self.id)])
        id_list = []

        for cheque in ids:
            id_list.append(cheque.id)
        action['domain'] = [('id', 'in', id_list)]
        
        return action

    @api.model
    def default_get(self, fields):
        res = super(AccountChequePayment, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        if not active_ids or active_model != 'account.move':
            return res
        invoices = self.env['account.move'].browse(active_ids)

        if invoices and len(invoices) == 1:
            invoice = invoices[0]

            if invoice.currency_id:
                res.update({'currency_id': invoice.currency_id,})
        
            if invoice.move_type in ('out_invoice', 'out_refund'):
                res.update({'payment_type': 'receive_money'})
        
            elif invoice.move_type in ('in_invoice', 'in_refund'):
                res.update({'payment_type': 'send_money'})

            res.update({
                'partner_id': invoice.partner_id.id,
                'payment_amount': invoice.amount_residual,
                'invoice_id': invoice.id,
                'due_date': invoice.invoice_date_due,
                'memo': invoice.name
            })

        return res

    @api.depends('payment_type','partner_id')
    def compute_account_moves(self):    
        self.account_move_ids = False
        domain = [('partner_id','=',self.partner_id.id),('payment_state','!=','paid'),('amount_residual','!=',0.0),('state','=','posted')]

        if self.payment_type == 'receive_money':
            domain.extend([('move_type', '=','out_invoice')])
        
        else:
            domain.extend([('move_type', '=','in_invoice')])

        moves = self.env['account.move'].search(domain)
        self.account_move_ids = moves.ids

    @api.depends('currency_cheque_id', 'payment_cheque_amount')
    def _compute_payment_amount(self):

        for record in self:
            record.payment_amount = record.currency_cheque_id._convert(
                record.payment_cheque_amount, self.env['res.currency'].search([('id', '=', record.currency_id.id)]), record.company_id, record.payment_date)

    @api.onchange('partner_id')
    def _onchange_partner(self):

        if self.env.company.auto_fill_open_invoice:
            domain = [('partner_id','=',self.partner_id.id),('payment_state','!=','paid'),('amount_residual','!=',0.0),('state','=','posted')]

            if self.payment_type == 'receive_money':
                domain.extend([('move_type', '=','out_invoice')])
            
            else:
                domain.extend([('move_type', '=','in_invoice')])

            moves = self.env['account.move'].search(domain)

            self.invoice_ids = [(6,0,moves.ids)]
    
    @api.onchange('invoice_ids')
    def onchange_invoice_ids(self):
        currency = self.invoice_ids[0].currency_id if len(self.invoice_ids) > 0 else self.env.company.currency_id
        
        for line in self.invoice_ids:
            if len(self.invoice_ids) > 0:

                if currency != line.currency_id:
                    raise UserError(f'Todas las facturas deben estar en la misma moneda.')
                
                else:
                    self.currency_id = line.currency_id

    def button_register(self):
        listt = []
        
        if self:
            if self.invoice_id:
                listt.append(self.invoice_id.id)
            
            if self.invoice_ids:
                listt.extend(self.invoice_ids.ids)

            self.write({
                'invoice_ids' : [(6,0,list(set(listt)))]
            })

            if self.cheque_status == 'draft':
                self.write({'state':'draft'})
            
            if self.cheque_status == 'deposit':
                self.action_register()
                self.action_deposited()
                self.write({'state':'deposited'})
            
            if self.cheque_status == 'paid':
                self.action_register()
                self.action_deposited()
                self.action_done()
                self.write({'state':'done'})

    def action_register(self):
        self.check_payment_amount()

        if self.invoice_ids:
            list_amount_residuals = self.invoice_ids.mapped('amount_residual')
            amount = (self.currency_id.round(sum(list_amount_residuals)) if self.currency_id else round(sum(list_amount_residuals), 2))
            
            if self.payment_amount  > amount and amount != 0:
                self.cheque_balance = self.payment_amount - amount

        self.write({'state': 'registered'})

    def check_payment_amount(self):
        if self.payment_amount <= 0.0:
            raise UserError('¡El importe debe ser mayor que cero!')

    def check_cheque_account(self):
        if self.payment_type == 'receive_money':
            if not self.env.company.cheque_customer:
                raise UserError('Por favor, configure la cuenta de pago de cheques para el cliente!')

            else:
                return self.env.company.cheque_customer.id

        else:
            if not self.env.company.cheque_supplier:
                raise UserError('¡Por favor, configure una cuenta de pago con cheque para el proveedor!')
            else:
                return self.env.company.cheque_supplier.id

    def get_partner_account(self):
        if self.payment_type == 'receive_money':
            return self.partner_id.property_account_receivable_id.id
        else:
            return self.partner_id.property_account_payable_id.id

    def action_returned(self):
        self.check_payment_amount()
        self.write({'state': 'returned'})

    def get_credit_move_line(self, account):
        return {
            'cheque_id': self.id,
            'account_id': account,
            'credit': self.payment_amount,
            'ref': self.memo,
            'date': self.payment_date,
            'date_maturity': self.due_date,
            'credit': self._currency_exchange()
        }

    def get_debit_move_line(self, account):
        return {
            'cheque_id': self.id,
            'account_id': account,
            'debit': self.payment_amount,
            'ref': self.memo,
            'date': self.payment_date,
            'date_maturity': self.due_date,
            'debit': self._currency_exchange(),
        }

    def _currency_exchange(self):
        return self.currency_id._convert(
            self.payment_amount, self.env['res.currency'].search([('id', '=', self.company_id.currency_id.id)]), self.company_id, self.payment_date)

    def get_move_vals(self, debit_line, credit_line):
        return {
            'cheque_id': self.id,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'ref': self.memo,
            'move_type':'entry',
            'line_ids': [(0, 0, debit_line),
                         (0, 0, credit_line)]
        }

    def action_deposited(self):
        self.ensure_one()
        self.check_payment_amount()

        # 1. Obtenemos las facturas a pagar, ORDENADAS por tu campo de secuencia.
        invoices_to_pay = self.invoice_ids.filtered(
            lambda inv: inv.payment_state != 'paid' and inv.amount_residual > 0
        ).sorted(key=lambda inv: inv.sequence or 0)

        if not invoices_to_pay:
            self.write({'state': 'deposited'})
            return

        # 2. Creamos el asiento contable del pago (tu lógica original es correcta).
        cheque_account_id = self.check_cheque_account()
        partner_account_id = self.get_partner_account()
        
        move_vals = {
            'ref': self.memo or f"Pago con cheque {self.cheque_nro}",
            'journal_id': self.journal_id.id,
            'date': self.payment_date,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {'partner_id': self.partner_id.id, 'account_id': cheque_account_id, 'debit': self.payment_amount, 'credit': 0.0}),
                (0, 0, {'partner_id': self.partner_id.id, 'account_id': partner_account_id, 'debit': 0.0, 'credit': self.payment_amount}),
            ],
        }
        deposit_move = self.env['account.move'].create(move_vals)
        deposit_move.action_post()
        self.deposit_move_id = deposit_move.id

        # 3. Lógica de conciliación MANUAL con saldo decreciente.
        
        # Obtenemos la línea de crédito del pago que vamos a usar.
        payment_credit_line = deposit_move.line_ids.filtered(
            lambda line: line.account_id.id == partner_account_id
        )
        
        amount_to_apply = self.payment_amount

        for invoice in invoices_to_pay:
            if amount_to_apply <= 0.01: # Usamos una pequeña tolerancia
                break

            # Obtenemos la línea por cobrar de la factura.
            invoice_debit_line = invoice.line_ids.filtered(
                lambda line: line.account_id.id == partner_account_id and not line.reconciled
            )
            
            if not invoice_debit_line:
                continue

            # Determinamos el monto a pagar para ESTA factura.
            amount_for_this_invoice = min(invoice.amount_residual, amount_to_apply)
            
            # --- LA MAGIA DE LA CONCILIACIÓN PARCIAL MANUAL ---
            self.env['account.partial.reconcile'].create({
                'debit_move_id': invoice_debit_line.id,
                'credit_move_id': payment_credit_line.id,
                'amount': amount_for_this_invoice,
                'debit_amount_currency': amount_for_this_invoice, # Asumimos misma moneda
                'credit_amount_currency': amount_for_this_invoice, # Asumimos misma moneda
            })
            # ----------------------------------------------------
            
            # Restamos el monto aplicado del saldo del cheque.
            amount_to_apply -= amount_for_this_invoice

        self.write({'state': 'deposited'})

    def action_bounced(self):
        self.action_cancel()

        # move = self.env['account.move']
        # self.check_payment_amount()
        # cheque_account = self.check_cheque_account()
        # partner_account = self.get_partner_account()
        # move_line_vals_debit = {}
        # move_line_vals_credit = {}

        # if self.payment_type == 'receive_money':
        #     move_line_vals_debit = self.get_debit_move_line(partner_account)
        #     move_line_vals_credit = self.get_credit_move_line(cheque_account)

        # else:
        #     move_line_vals_debit = self.get_debit_move_line(cheque_account)
        #     move_line_vals_credit = self.get_credit_move_line(partner_account)

        # if self.memo:
        #     move_line_vals_debit.update({'name': 'Cheque payment :'+self.memo})
        #     move_line_vals_credit.update({'name': 'Cheque payment :'+self.memo})

        # else:
        #     move_line_vals_debit.update({'name': 'Cheque payment'})
        #     move_line_vals_credit.update({'name': 'Cheque payment'})

        # move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        # total_amount_residuals = sum(self.invoice_ids.mapped('amount_residual'))

        # if self.invoice_ids and total_amount_residuals != 0:
        #     move_id = move.create(move_vals)
        #     move_id.action_post()

        self.write({'state': 'bounced'})

    def action_done(self):
        self.check_payment_amount()

        # Lógica de obtención de cuenta pendiente de banco para Odoo 18
        # Debe distinguir entre cobros y pagos.
        if self.payment_type == 'receive_money':
            outstanding_accounts = self.journal_id._get_journal_inbound_outstanding_payment_accounts()
        else: # send_money
            outstanding_accounts = self.journal_id._get_journal_outbound_outstanding_payment_accounts()

        if not outstanding_accounts:
            raise UserError(_("No outstanding account found for journal '%s'.", self.journal_id.name))
        bank_account_id = outstanding_accounts[0].id

        cheque_account_id = self.check_cheque_account()
        
        # Lógica de asientos para el segundo paso (Cobro del cheque)
        # Este asiento mueve el saldo de la cuenta de cheques a la cuenta del banco.
        if self.payment_type == 'receive_money':
            # DEBE: Banco (Cuenta pendiente), HABER: Cheques en Cartera
            move_line_vals_debit = self.get_debit_move_line(bank_account_id)
            move_line_vals_credit = self.get_credit_move_line(cheque_account_id)
        else:
            # DEBE: Cheques por Pagar, HABER: Banco (Cuenta pendiente)
            move_line_vals_debit = self.get_debit_move_line(cheque_account_id)
            move_line_vals_credit = self.get_credit_move_line(bank_account_id)

        # Añadir partner_id para trazabilidad
        move_line_vals_debit['partner_id'] = self.partner_id.id
        move_line_vals_credit['partner_id'] = self.partner_id.id

        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        
        # Este asiento se crea siempre que el cheque se marca como hecho.
        clearance_move = self.env['account.move'].create(move_vals)
        clearance_move.action_post()
        
        self.write({
            'state': 'done',
            'done_date': date.today(),
        })

        # La creación del pago por el sobrepago/saldo está bien.
        if self.cheque_balance > 0:
            payment = self.env['account.payment'].create({
                'payment_type': 'inbound' if self.payment_type == 'receive_money' else 'outbound',
                'partner_id': self.partner_id.id,
                'amount': self.cheque_balance,
                'date': fields.Date.today(),
                'memo': _('Overpayment for cheque %s', self.name),
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id.id, # Usar la moneda del pago, no la del cheque
            })
            payment.action_post()
            self.payment_id = payment.id

    def action_cancel(self):
        self.action_delete_related_moves()

        if self.company_id.cheque_operation_type == 'cancel':
            self.write({'state': 'cancel'})
        
        elif self.company_id.cheque_operation_type == 'cancel_draft':
            self.write({'state': 'draft'})
        
        elif self.company_id.cheque_operation_type == 'cancel_delete':
            self.write({'state': 'draft'})
            self.unlink()

        if self.payment_id:
            self.payment_id.action_draft()
            self.payment_id.unlink()
    
    def action_cheque_cancel(self):
        self.action_delete_related_moves()
        self.write({'state': 'cancel'})

    def action_cheque_cancel_draft(self):
        self.action_delete_related_moves()
        self.write({'state': 'draft'})
    
    def action_cheque_cancel_delete(self):
        self.action_delete_related_moves()
        self.write({'state': 'draft'})
        self.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payment_type') == 'receive_money':
                vals['name'] = self.env['ir.sequence'].next_by_code('cheque.payment.customer')

            elif vals.get('payment_type') == 'send_money':
                vals['name'] = self.env['ir.sequence'].next_by_code('cheque.payment.supplier')

        records = super().create(vals_list)

        records.mapped('attachment_ids').write({'res_id': records.id})

        return records
    
    @api.model
    def notify_customer_due_date(self):
        emails = []

        if self.env.company.is_cust_due_notify:
            notify_day_1 = self.env.company.notify_on_1
            notify_day_2 = self.env.company.notify_on_2
            notify_day_3 = self.env.company.notify_on_3
            notify_day_4 = self.env.company.notify_on_4
            notify_day_5 = self.env.company.notify_on_5
            notify_date_1 = False
            notify_date_2 = False
            notify_date_3 = False
            notify_date_4 = False
            notify_date_5 = False
            if notify_day_1:
                notify_date_1 = fields.date.today() + timedelta(days=int(notify_day_1)*-1)
            if notify_day_2:
                notify_date_2 = fields.date.today() + timedelta(days=int(notify_day_2)*-1)
            if notify_day_3:
                notify_date_3 = fields.date.today() + timedelta(days=int(notify_day_3)*-1)
            if notify_day_4:
                notify_date_4 = fields.date.today() + timedelta(days=int(notify_day_4)*-1)
            if notify_day_5:
                notify_date_5 = fields.date.today() + timedelta(days=int(notify_day_5)*-1)
            
            records = self.search([('payment_type','=','receive_money')])
            for user in self.env.company.cmc_user_ids:
                    if user.partner_id and user.partner_id.email:
                        emails.append(user.partner_id.email)
            email_values = {'email_to': ','.join(emails),}
            view = self.env.ref('cheque_management_cross.account_cheque_payment_form', raise_if_not_found=False).sudo()
            view_id = view.id if view else 0

            for record in records:
                if (record.due_date == notify_date_1
                    or record.due_date == notify_date_2
                    or record.due_date == notify_date_3
                    or record.due_date == notify_date_4
                    or record.due_date == notify_date_5):
                    
                    if self.env.company.is_notify_to_customer:
                        template_download_id = self.env.ref('cheque_management_cross.cmc_company_to_customer_notification')
                        _ = record.env['mail.template'].browse(template_download_id.id).send_mail(record.id, notif_layout='mail.mail_notification_light', force_send=True)

                    if self.env.company.is_notify_to_user and self.env.company.cmc_user_ids:
                        url = ''
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        url = base_url + "/web#id=" + \
                                str(record.id) + \
                                "&&model=account.cheque.payment&view_type=form&view_id=" + str(view_id)
                        ctx = {"customer_url": url,}
                        template_download_id = self.env.ref('cheque_management_cross.cmc_company_to_int_user_notification')
                        _ = request.env['mail.template'].sudo().browse(template_download_id.id).with_context(ctx).send_mail(
                            record.id, email_values=email_values, notif_layout='mail.mail_notification_light', force_send=True)
                        
    @api.model
    def notify_vendor_due_date(self):
        emails = []

        if self.env.company.is_supplier_due_notify:
            notify_day_1_ven = self.env.company.notify_on_1_supplier
            notify_day_2_ven = self.env.company.notify_on_2_supplier
            notify_day_3_ven = self.env.company.notify_on_3_supplier
            notify_day_4_ven = self.env.company.notify_on_4_supplier
            notify_day_5_ven = self.env.company.notify_on_5_supplier
            notify_date_1_ven = False
            notify_date_2_ven = False
            notify_date_3_ven = False
            notify_date_4_ven = False
            notify_date_5_ven = False

            if notify_day_1_ven:
                notify_date_1_ven = fields.date.today() + timedelta(days=int(notify_day_1_ven)*-1)

            if notify_day_2_ven:
                notify_date_2_ven = fields.date.today() + timedelta(days=int(notify_day_2_ven)*-1)

            if notify_day_3_ven:
                notify_date_3_ven = fields.date.today() + timedelta(days=int(notify_day_3_ven)*-1)

            if notify_day_4_ven:
                notify_date_4_ven = fields.date.today() + timedelta(days=int(notify_day_4_ven)*-1)

            if notify_day_5_ven:
                notify_date_5_ven = fields.date.today() + timedelta(days=int(notify_day_5_ven)*-1)

            records = self.search([('payment_type','=','send_money')])

            for user in self.env.company.cmc_user_ids_vendor:
                if user.partner_id and user.partner_id.email:
                    emails.append(user.partner_id.email)
            email_values = {'email_to': ','.join(emails),}
            view = self.env.ref("cheque_management_cross.account_cheque_payment_form", raise_if_not_found=False)
            view_id = view.id if view else 0

            for record in records:
                if (record.due_date == notify_date_1_ven
                    or record.due_date == notify_date_2_ven
                    or record.due_date == notify_date_3_ven
                    or record.due_date == notify_date_4_ven
                    or record.due_date == notify_date_5_ven):
                    
                    if self.env.company.is_notify_to_vendor:
                        template_download_id = self.env.ref('cheque_management_cross.cmc_company_to_customer_notification')
                        _ = record.env['mail.template'].browse(template_download_id.id).send_mail(record.id, notif_layout='mail.mail_notification_light', force_send=True)

                    if self.env.company.is_notify_to_user_supplier and self.env.company.cmc_user_ids_supplier:
                        url = ''
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        url = base_url + "/web#id=" + \
                                str(record.id) + \
                                "&&model=account.cheque.payment&view_type=form&view_id=" + str(view_id)
                        ctx = {"customer_url": url,}
                        template_download_id = self.env.ref('cheque_management_cross.cmc_company_to_int_user_notification')
                        _ = request.env['mail.template'].sudo().browse(template_download_id.id).with_context(ctx).send_mail(
                            record.id, email_values=email_values, notif_layout='mail.mail_notification_light', force_send=True)

    def action_set_draft(self):
        self.sudo().write({'state':'draft',})

    def action_delete_related_moves(self):
        # Es una buena práctica usar sudo() para asegurar los permisos necesarios.
        AccountMove = self.env['account.move'].sudo()
        
        for cheque in self:
            # 1. Buscamos el asiento contable creado por este cheque.
            #    Para que esto sea 100% fiable, DEBEMOS tener un enlace directo.
            #    Vamos a añadirlo.
            
            if not cheque.deposit_move_id:
                # Si no hay asiento que borrar, no hacemos nada para este cheque.
                continue

            move_to_delete = cheque.deposit_move_id

            # 2. Verificamos que el asiento no esté ya cancelado o borrado.
            if move_to_delete.state == 'posted':
                # Lo pasamos a borrador. Odoo se encarga de romper
                # automáticamente todas las conciliaciones asociadas a sus líneas.
                move_to_delete.button_draft()

            # 3. Eliminamos el asiento contable.
            move_to_delete.unlink()

            # 4. Limpiamos la referencia en nuestro cheque y reseteamos la fecha.
            cheque.sudo().write({
                'done_date': False,
                'deposit_move_id': False,
            })

    def action_state_register(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        
        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')
            
            if len(set(states)) == 1:
                if states[0] == 'draft':
                    for active_model in active_models:
                        active_model.action_register()

                else:
                    raise UserError('¡Sólo la verificación de cheque en estado Borrador puede cambiar al estado Registrado!')

            else:
                raise UserError('¡Los estados deben ser iguales!')

    def action_state_return(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] == 'registered':
                    for active_model in active_models:
                        active_model.action_returned()

                else:
                    raise UserError('¡Sólo el cheque en estado de registro puede cambiar al estado de devolución!')

            else:
                raise UserError('¡Los estados deben ser iguales!')

    def action_state_deposit(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] in ['registered','returned','bounced']:
                    for active_model in active_models:
                        active_model.action_deposited()

                else:
                    raise UserError('¡Solo los cheques registrados, devueltos y rebotados pueden cambiar al estado de depósito!')

            else:
                raise UserError('¡Los estados deben ser iguales!')
        
    def action_state_bounce(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] == 'deposited':
                    for active_model in active_models:
                        active_model.action_bounced()

                else:
                    raise UserError('¡Sólo el cheque en estado de depósito puede cambiar al estado de rebote!')

            else:
                raise UserError('¡Los estados deben ser iguales!')

    def action_state_done(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] == 'deposited':
                    for active_model in active_models:
                        active_model.action_done()

                else:
                    raise UserError('¡Sólo el cheque en estado de depósito puede cambiar al estado realizado!')

            else:
                raise UserError('¡Los estados deben ser iguales!')

    def action_state_cancel(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] in ['registered','returned','bounced']:
                    for active_model in active_models:
                        active_model.action_cancel()

                else:
                    raise UserError('¡Sólo los cheques registrados, devueltos y rebotados pueden cambiar al estado de cancelación!')

            else:
                raise UserError('¡Los estados deben ser iguales!')

    def action_skip_steps(self):
        self.action_deposited()
        self.action_done()
        self.write({'state': 'paid'})

    def action_finish(self):
        self.write({'state': 'done'})


class IrAttachmentInherit(models.Model):
    _inherit = 'ir.attachment'

    cheque_id = fields.Many2one(
        'account.cheque.payment', string='Cheque')
