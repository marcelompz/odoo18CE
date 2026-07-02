# -*- coding: utf-8 -*-
"""Extension de hr.payslip para mostrar las filas del Tablero Diario y
las marcaciones detalladas (hr.attendance) del periodo de la nomina como
pestanas de visualizacion (read-only).
"""
from odoo import _, api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_report_ids = fields.One2many(
        'hr.attendance.daily.report', compute='_compute_attendance_report_ids',
        string='Tablero Diario del periodo',
    )
    attendance_ids_period = fields.One2many(
        'hr.attendance', compute='_compute_attendance_ids_period',
        string='Marcaciones detalladas del periodo',
    )
    attendance_total_hours = fields.Float(
        string='Total horas del periodo',
        compute='_compute_attendance_totals',
    )
    attendance_total_cost = fields.Monetary(
        string='Costo total del periodo',
        compute='_compute_attendance_totals',
        currency_field='attendance_currency_id',
    )
    attendance_currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        compute='_compute_attendance_totals', store=False,
    )
    attendance_present_days = fields.Integer(
        string='Dias presentes',
        compute='_compute_attendance_totals',
    )
    attendance_absence_days = fields.Integer(
        string='Faltas',
        compute='_compute_attendance_totals',
    )
    attendance_leave_days = fields.Integer(
        string='Vacaciones / Licencia',
        compute='_compute_attendance_totals',
    )
    attendance_rest_days = fields.Integer(
        string='Descanso / Feriado',
        compute='_compute_attendance_totals',
    )

    cn_dias_trabajados = fields.Integer(
        string='Dias trabajados',
        compute='_compute_cn_payroll_summary',
        help='Cantidad de dias presentes del periodo segun el Tablero Diario.',
    )
    cn_horas_trabajadas = fields.Float(
        string='Horas trabajadas',
        compute='_compute_cn_payroll_summary',
    )
    cn_total_ingresos = fields.Monetary(
        string='Total Ingresos',
        compute='_compute_cn_payroll_summary',
        currency_field='currency_id',
        help='Suma de Bruto + Bonificaciones (BASIC + ALW).',
    )
    cn_total_descuentos = fields.Monetary(
        string='Total Descuentos',
        compute='_compute_cn_payroll_summary',
        currency_field='currency_id',
        help='Suma de IPS, Anticipos, FALTAS, Embargos, etc. (DED).',
    )
    cn_total_neto = fields.Monetary(
        string='Neto Desembolsado',
        compute='_compute_cn_payroll_summary',
        currency_field='currency_id',
        help='Liquido a percibir (NET).',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        compute='_compute_cn_currency_id', store=False,
    )

    # Crossnexion: pagos relacionados al recibo (via reconciliation)
    payment_ids = fields.Many2many(
        'account.payment',
        string='Pagos del recibo',
        compute='_compute_payment_ids',
    )
    payment_count = fields.Integer(
        string='Cant. Pagos',
        compute='_compute_payment_ids',
    )

    def _compute_cn_currency_id(self):
        for slip in self:
            slip.currency_id = (slip.employee_id.company_id.currency_id
                                or self.env.company.currency_id)

    @api.depends('move_id', 'move_id.line_ids', 'state')
    def _compute_payment_ids(self):
        Payment = self.env['account.payment']
        for slip in self:
            if not slip.move_id:
                slip.payment_ids = Payment
                slip.payment_count = 0
                continue
            # Buscar moves conciliados con las lineas del asiento del recibo
            reconciled_moves = (
                slip.move_id.line_ids.matched_debit_ids.debit_move_id.move_id
                | slip.move_id.line_ids.matched_credit_ids.credit_move_id.move_id
            )
            # account.move.origin_payment_id apunta al account.payment origen
            if 'origin_payment_id' in self.env['account.move']._fields:
                payments = reconciled_moves.origin_payment_id
            else:
                payments = Payment.search([('move_id', 'in', reconciled_moves.ids)])
            slip.payment_ids = payments
            slip.payment_count = len(payments)

    def action_open_payments(self):
        self.ensure_one()
        if not self.payment_ids:
            from odoo.exceptions import UserError
            raise UserError(_('Este recibo aun no tiene pagos asociados.'))
        if len(self.payment_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Pago del recibo'),
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': self.payment_ids.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pagos del recibo'),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.payment_ids.ids)],
            'context': {'create': False},
            'target': 'current',
        }

    def _compute_cn_payroll_summary(self):
        for slip in self:
            ingresos = 0.0
            descuentos = 0.0
            neto = 0.0
            for line in slip.line_ids:
                cat = line.category_id.code or ''
                if cat in ('BASIC', 'ALW'):
                    ingresos += line.total or 0.0
                elif cat == 'DED':
                    descuentos += abs(line.total or 0.0)
                elif cat == 'NET':
                    neto += line.total or 0.0
            slip.cn_total_ingresos = ingresos
            slip.cn_total_descuentos = descuentos
            slip.cn_total_neto = neto
            rows = slip.attendance_report_ids
            slip.cn_dias_trabajados = len([
                r for r in rows if r.absence_status == 'present'
            ])
            slip.cn_horas_trabajadas = sum(rows.mapped('hours_total'))

    def _compute_attendance_report_ids(self):
        Report = self.env['hr.attendance.daily.report'].sudo()
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                slip.attendance_report_ids = False
                continue
            rows = Report.search([
                ('employee_id', '=', slip.employee_id.id),
                ('date', '>=', slip.date_from),
                ('date', '<=', slip.date_to),
            ], order='date asc')
            slip.attendance_report_ids = rows

    def _compute_attendance_ids_period(self):
        Att = self.env['hr.attendance'].sudo()
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                slip.attendance_ids_period = False
                continue
            if 'shift_date' in Att._fields:
                domain = [
                    ('employee_id', '=', slip.employee_id.id),
                    ('shift_date', '>=', slip.date_from),
                    ('shift_date', '<=', slip.date_to),
                ]
            else:
                date_from_dt = fields.Datetime.to_datetime(slip.date_from)
                date_to_dt = fields.Datetime.to_datetime(slip.date_to).replace(
                    hour=23, minute=59, second=59)
                domain = [
                    ('employee_id', '=', slip.employee_id.id),
                    ('check_in', '>=', date_from_dt),
                    ('check_in', '<=', date_to_dt),
                ]
            atts = Att.search(domain, order='check_in asc')
            slip.attendance_ids_period = atts

    def _compute_attendance_totals(self):
        for slip in self:
            rows = slip.attendance_report_ids
            slip.attendance_currency_id = (slip.employee_id.company_id.currency_id
                                           or self.env.company.currency_id)
            if not rows:
                slip.attendance_total_hours = 0.0
                slip.attendance_total_cost = 0.0
                slip.attendance_present_days = 0
                slip.attendance_absence_days = 0
                slip.attendance_leave_days = 0
                slip.attendance_rest_days = 0
                continue
            slip.attendance_total_hours = sum(rows.mapped('hours_total'))
            slip.attendance_total_cost = sum(rows.mapped('daily_cost'))
            slip.attendance_present_days = len([
                r for r in rows if r.absence_status == 'present'
            ])
            slip.attendance_absence_days = len([
                r for r in rows if r.absence_status == 'absence'
            ])
            slip.attendance_leave_days = len([
                r for r in rows if r.absence_status == 'leave'
            ])
            slip.attendance_rest_days = len([
                r for r in rows if r.absence_status == 'rest'
            ])

    def action_recalculate_attendance(self):
        self.ensure_one()
        Report = self.env['hr.attendance.daily.report'].sudo()
        Report.regenerate(
            date_from=self.date_from,
            date_to=self.date_to,
            employee_ids=[self.employee_id.id] if self.employee_id else None,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tablero recalculado'),
                'message': _('Marcaciones del periodo regeneradas. '
                             'Vuelva a calcular la nomina si es necesario.'),
                'type': 'success',
            },
        }

    def action_request_falta_approval_period(self):
        self.ensure_one()
        faltas = self.attendance_report_ids.filtered(
            lambda r: r.absence_status == 'absence'
        )
        if not faltas:
            from odoo.exceptions import UserError
            raise UserError(_('No hay dias en estado FALTA en este periodo.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitar Aprobacion de FALTAS del periodo'),
            'res_model': 'hr.falta.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': faltas.ids,
                'active_model': 'hr.attendance.daily.report',
            },
        }

    def action_open_attendances_period(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Marcaciones %s - %s a %s') % (
                self.employee_id.name or '', self.date_from, self.date_to),
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('shift_date', '>=', self.date_from),
                ('shift_date', '<=', self.date_to),
            ],
            'context': {
                'default_employee_id': self.employee_id.id,
            },
            'target': 'current',
        }

    def action_print_payslip_internal(self):
        self.ensure_one()
        Report = self.env['ir.actions.report'].sudo()
        report = Report.search([
            ('report_name', '=', 'hr_payslip_bulk_print_cross.report_payslip_mtess_planilla'),
        ], limit=1)
        if not report:
            report = Report.search([
                ('model', '=', 'hr.payslip'),
                ('report_type', '=', 'qweb-pdf'),
            ], limit=1)
        if not report:
            from odoo.exceptions import UserError
            raise UserError(_('No se encontro un reporte de recibo configurado.'))
        return report.report_action(self)

    def action_print_payslip_ips(self):
        self.ensure_one()
        Report = self.env['ir.actions.report'].sudo()
        report = Report.search([
            ('report_name', '=', 'l10n_py_hr_payroll_report.report_payslip_funcionario'),
        ], limit=1)
        if not report:
            report = Report.search([
                ('report_name', '=', 'hr_payroll.report_payslip'),
            ], limit=1)
        if not report:
            report = Report.search([
                ('model', '=', 'hr.payslip'),
                ('report_type', '=', 'qweb-pdf'),
            ], limit=1)
        if not report:
            from odoo.exceptions import UserError
            raise UserError(_('No se encontro un reporte IPS configurado.'))
        return report.report_action(self)

    # === ASIENTO CONTABLE: excluir reglas informativas/totalizadoras ===
    _CN_RULES_EXCLUDED_FROM_MOVE = (
        'CN_SALARIO_NETO', 'CN_INGRESO_TOTAL', 'NET',
    )

    def _action_create_account_move(self):
        """Override: vacia temporalmente account_debit/account_credit en las
        reglas excluidas durante la generacion del asiento, y las restaura
        despues. El super() no incluye esas lineas en el asiento, pero el
        wizard de Pago sigue viendo las cuentas conciliables."""
        super_method = getattr(super(), '_action_create_account_move', None)
        if super_method is None:
            return None
        Rule = self.env['hr.salary.rule'].sudo()
        rules_to_blank = Rule.with_context(active_test=False).search([
            ('code', 'in', list(self._CN_RULES_EXCLUDED_FROM_MOVE))
        ])
        backup = {}
        for r in rules_to_blank:
            backup[r.id] = (
                r.account_debit.id if r.account_debit else False,
                r.account_credit.id if r.account_credit else False,
            )
        try:
            if rules_to_blank:
                rules_to_blank.write({
                    'account_debit': False,
                    'account_credit': False,
                })
            return super_method()
        finally:
            for rid, (deb, cred) in backup.items():
                try:
                    Rule.browse(rid).write({
                        'account_debit': deb,
                        'account_credit': cred,
                    })
                except Exception:
                    pass

    def action_register_payment(self):
        """Override de hr_payroll_account.action_register_payment.

        Dos cambios respecto al estandar:
        1) Validacion adaptada: acepta NET / CN_SALARIO_NETO / categoria NET
           con account_credit conciliable (el original solo busca code='NET').
        2) Filtra las lineas pasadas al wizard de pago: solo las de la cuenta
           de credito de la regla NET (ej. 2.1.1.01 Sueldos a Pagar) que
           todavia no esten conciliadas. Asi se genera UN solo pago al
           empleado por el neto, en lugar de un pago por cada liability del
           asiento (IPS Trabajador, IPS Patronal, Anticipos, etc., que se
           pagan por separado al IPS u otras partes).
        """
        from odoo.exceptions import UserError
        super_method = getattr(super(), 'action_register_payment', None)
        if super_method is None:
            return None
        if any(state == 'paid' for state in self.mapped('state')):
            raise UserError(_('You can only register payments for unpaid documents.'))
        # Identificar la cuenta de credito de la regla NET (Sueldos a Pagar)
        # para filtrar solo esas lineas en el wizard.
        net_credit_accounts = self.env['account.account']
        for slip in self:
            if not slip.struct_id:
                continue
            net_candidates = slip.struct_id.with_context(active_test=False).rule_ids.filtered(
                lambda r: r.code in ('NET', 'CN_SALARIO_NETO')
                or (r.category_id and r.category_id.code == 'NET')
            )
            ok = any(
                r.account_credit and r.account_credit.reconcile
                for r in net_candidates
            )
            if not ok:
                raise UserError(_(
                    'Ninguna regla NET (NET / CN_SALARIO_NETO / categoria '
                    'NET) en la estructura "%s" tiene cuenta de credito '
                    'conciliable. Ejecute "Configurar Plan de Cuentas PY '
                    '(Res. 49/14)" sobre la estructura.'
                ) % slip.struct_id.name)
            # Acumular las cuentas de credito conciliables de las reglas NET
            for r in net_candidates:
                if r.account_credit and r.account_credit.reconcile:
                    net_credit_accounts |= r.account_credit
        bank_account = self.employee_id.sudo().bank_account_id
        if not bank_account.allow_out_payment:
            raise UserError(_('The employee bank account is untrusted'))
        if any(m.state != 'posted' for m in self.move_id):
            raise UserError(_('You can only register payment for posted journal entries.'))
        # Filtrar solo las lineas de las cuentas NET, no conciliadas, con
        # saldo pendiente. Asi el wizard genera UN solo pago al empleado.
        if net_credit_accounts:
            relevant_lines = self.move_id.line_ids.filtered(
                lambda l: l.account_id in net_credit_accounts
                and not l.full_reconcile_id
                and (l.debit or l.credit)
            )
            if not relevant_lines:
                # Fallback: si por alguna razon no hay lineas (todas
                # conciliadas), abrir el wizard con todas como antes.
                relevant_lines = self.move_id.line_ids
        else:
            relevant_lines = self.move_id.line_ids
        return relevant_lines.action_register_payment(
            ctx={
                'default_partner_id': self.employee_id.work_contact_id.id,
                'default_partner_bank_id': bank_account.id,
                'default_company_id': self.company_id.id,
                # group_payment=True hace que todas las lineas de la misma
                # cuenta/partner se consoliden en UN solo pago. Sin esto,
                # se crea un pago por cada linea (Bruto, Bonif, HE, IPS_TRAB,
                # etc) aun siendo de la misma cuenta '2.1.1.01'.
                'default_group_payment': True,
            },
        )
