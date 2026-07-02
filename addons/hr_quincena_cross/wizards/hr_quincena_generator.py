# -*- coding: utf-8 -*-
"""Wizard: Generar Quincenas del periodo.

Para cada empleado activo cuyo contrato tenga cn_paga_quincena=True, calcula
el anticipo quincenal automatico y lo desembolsa.

Formula (Paraguay, mensualizado, sin descontar faltas):
  dias_disponibles = dias del [max(date_inicio_contrato, dia_1_mes), dia_15_mes]
  proporcion       = dias_disponibles / 15
  bruto            = wage x 0.5 x proporcion
  ips              = wage x 0.09 x 0.5 x proporcion
  extraordinarios  = Σ(prestamos pending_in_quincena=True del empleado)
  neto_quincena    = bruto - ips + extraordinarios

Crea un hr.advance tipo "quincena" por el neto, lo aprueba y desembolsa.
Marca los prestamos extraordinarios como absorbidos (quincena_advance_id).
"""
from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


# Tasa IPS Empleado (Paraguay): 9% del bruto
IPS_EMPLEADO_RATE = 0.09
# Porcentaje del salario que se anticipa en la quincena
QUINCENA_SALARIO_RATE = 0.50
# Porcentaje del IPS Empleado que se descuenta en la quincena (50% del 9%)
QUINCENA_IPS_RATE = 0.50


class HrQuincenaGenerator(models.TransientModel):
    _name = 'hr.quincena.generator'
    _description = 'Wizard: Generar Quincenas del periodo'

    quincena_date = fields.Date(
        string='Fecha de la quincena', required=True,
        default=lambda self: self._default_quincena_date(),
        help='Fecha del corte de la quincena (normalmente el 15 del mes).',
    )
    department_ids = fields.Many2many(
        'hr.department', string='Departamentos (vacio = todos)',
    )
    employee_ids = fields.Many2many(
        'hr.employee', string='Empleados (vacio = todos los que aplican)',
    )
    include_extraordinarios = fields.Boolean(
        string='Incluir adelantos extraordinarios pendientes',
        default=True,
        help='Si esta activo, suma al neto los prestamos/uniformes/otros con '
             'pending_in_quincena=True para los empleados procesados.',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario de pago',
        domain=[('type', 'in', ('bank', 'cash'))],
        default=lambda self: self.env.company.cn_quincena_journal_id,
        required=True,
        help='Diario en el que se registra el account.payment de cada quincena.',
    )
    advance_account_id = fields.Many2one(
        'account.account',
        string='Cuenta anticipo a empleados',
        required=True,
        default=lambda self: self._default_advance_account(),
        help='Cuenta contable de destino del pago (Anticipo a Empleados). '
             'Se usa como destination_account_id en el account.payment.',
    )
    dry_run = fields.Boolean(
        string='Simulacion (no genera nada)', default=False,
        help='Si esta activo, calcula y muestra el detalle por empleado sin crear '
             'los anticipos ni los pagos. Util para revisar antes de ejecutar.',
    )

    @api.model
    def _default_advance_account(self):
        prev = self.env['hr.advance'].search(
            [('advance_account_id', '!=', False)],
            order='date desc', limit=1,
        )
        return prev.advance_account_id if prev else False

    @api.model
    def _default_quincena_date(self):
        today = fields.Date.context_today(self)
        dia = self.env.company.cn_quincena_dia or 15
        try:
            return today.replace(day=dia)
        except ValueError:
            return today

    # ------------------------------------------------------------------
    # Accion principal
    # ------------------------------------------------------------------
    def action_generate(self):
        self.ensure_one()
        Employee = self.env['hr.employee']
        Contract = self.env['hr.contract']

        # 1) Buscar empleados elegibles: con contrato vigente y cn_paga_quincena=True
        domain_emp = []
        if self.employee_ids:
            domain_emp.append(('id', 'in', self.employee_ids.ids))
        if self.department_ids:
            domain_emp.append(('department_id', 'in', self.department_ids.ids))
        all_emps = Employee.search(domain_emp)

        # Filtrar por contrato vigente con cn_paga_quincena
        eligible = []
        for emp in all_emps:
            contract = self._get_active_contract(emp, self.quincena_date)
            if not contract:
                continue
            if not contract.cn_paga_quincena:
                continue
            if not contract.wage:
                continue
            eligible.append((emp, contract))

        if not eligible:
            raise UserError(_(
                'No hay empleados elegibles. Verifique:\n'
                ' - Que tengan contrato vigente a la fecha %s.\n'
                ' - Que el contrato tenga marcado "Aplica pago de quincena".\n'
                ' - Que el contrato tenga un salario (wage) configurado.'
            ) % self.quincena_date)

        # 2) Procesar cada empleado
        created = self.env['hr.advance']
        details = []
        skipped = []
        for emp, contract in eligible:
            try:
                with self.env.cr.savepoint():
                    # Evitar duplicado: ya existe quincena para este empleado en
                    # el mismo mes que la fecha indicada?
                    existing = self.env['hr.advance'].search([
                        ('employee_id', '=', emp.id),
                        ('advance_type', '=', 'quincena'),
                        ('quincena_date', '>=', self.quincena_date.replace(day=1)),
                        ('quincena_date', '<=', self.quincena_date),
                        ('state', 'not in', ('cancelled',)),
                    ], limit=1)
                    if existing:
                        skipped.append((emp, _('Ya existe quincena en este periodo: %s') % existing.name))
                        continue

                    vals = self._calc_quincena_for(emp, contract)
                    if vals['neto'] <= 0:
                        skipped.append((emp, _('Neto calculado <= 0 (%s)') % vals['neto']))
                        continue

                    if self.dry_run:
                        details.append((emp, vals, None))
                        continue

                    advance = self._create_quincena_advance(emp, contract, vals)
                    created |= advance
                    details.append((emp, vals, advance))
            except Exception as e:
                skipped.append((emp, str(e)))
                continue

        # 3) Construir mensaje de resultado y retornar
        msg = _('Procesados: %d empleados. Generadas: %d quincenas.') % (
            len(eligible), len(created))
        if skipped:
            msg += _('\nOmitidos: %d:') % len(skipped)
            for emp, reason in skipped:
                msg += '\n  • %s: %s' % (emp.name, reason)
        if self.dry_run:
            msg += _('\n(SIMULACION: no se creo ningun registro)')

        # Postear log con detalles en cada advance creado
        for emp, vals, adv in details:
            if adv:
                body = self._build_audit_message(emp, vals)
                adv.message_post(body=body)

        # Si dry_run, mostrar tabla. Sino, abrir la lista de quincenas creadas
        if self.dry_run or not created:
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': _('Quincenas - simulacion' if self.dry_run else 'Quincenas'),
                    'message': msg, 'type': 'success' if not skipped else 'warning',
                    'sticky': True,
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quincenas generadas'),
            'res_model': 'hr.advance',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'context': {'create': False, 'search_default_group_state': 1},
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_active_contract(self, employee, ref_date):
        Contract = self.env['hr.contract']
        return Contract.search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ('open', 'close')),
            ('date_start', '<=', ref_date),
            '|', ('date_end', '=', False), ('date_end', '>=', ref_date),
        ], order='date_start desc', limit=1)

    def _calc_dias_disponibles(self, employee, contract):
        """Dias de [max(date_inicio_contrato, dia_1_mes), dia_15_mes].
        NO descuenta faltas (eso es politica de la empresa: las faltas se
        descuentan SOLO en el recibo de fin de mes)."""
        qd = self.quincena_date
        day_1 = qd.replace(day=1)
        start = max(contract.date_start or day_1, day_1)
        if start > qd:
            return 0
        # Ambos extremos incluidos
        return (qd - start).days + 1

    def _calc_quincena_for(self, employee, contract):
        wage = contract.wage or 0.0
        dias_disp = self._calc_dias_disponibles(employee, contract)
        proporcion = (dias_disp / 15.0) if dias_disp else 0.0
        bruto = wage * QUINCENA_SALARIO_RATE * proporcion
        ips   = wage * IPS_EMPLEADO_RATE * QUINCENA_IPS_RATE * proporcion

        # -- Beneficios/prestamos pendientes de primera deduccion en quincena --
        # El efectivo ya fue entregado al empleado por finanzas (state='paid').
        # La quincena descuenta:
        #   - Fraccionado (prestamo/uniforme en cuotas): 50% de la cuota mensual
        #   - No fraccionado (uniforme/beneficio de pago unico): monto completo
        recupero_beneficio = 0.0
        pending_loans = self.env['hr.loan']
        if self.include_extraordinarios:
            pending_loans = self.env['hr.loan'].search([
                ('employee_id', '=', employee.id),
                ('pending_in_quincena', '=', True),
                ('state', '=', 'paid'),
                ('quincena_advance_id', '=', False),
            ])
            for loan in pending_loans:
                if loan.is_fractional:
                    recupero_beneficio += loan.amount_per_installment * 0.5
                else:
                    recupero_beneficio += loan.amount_total

        # -- Cuotas 50% de prestamos fraccionados ya absorbidos en quincenas anteriores --
        deduccion_cuotas = 0.0
        active_loans = self.env['hr.loan'].search([
            ('employee_id', '=', employee.id),
            ('is_fractional', '=', True),
            ('salary_attachment_id', '!=', False),
            ('state', 'in', ('paid', 'in_progress')),
            ('quincena_advance_id', '!=', False),  # ya absorbido, evita doble conteo
        ])
        for loan in active_loans:
            attach = loan.salary_attachment_id
            if (attach.state == 'open'
                    and attach.date_start
                    and attach.date_start <= self.quincena_date):
                deduccion_cuotas += loan.amount_per_installment * 0.5

        neto = bruto - ips - recupero_beneficio - deduccion_cuotas
        return {
            'wage': wage,
            'dias_disp': dias_disp,
            'proporcion': proporcion,
            'bruto': bruto,
            'ips': ips,
            'extras': 0.0,          # campo legacy, ya no se usa como suma
            'recupero_beneficio': recupero_beneficio,
            'deduccion_cuotas': deduccion_cuotas,
            'neto': neto,
            'pending_loans': pending_loans,
        }

    def _create_quincena_advance(self, employee, contract, vals):
        """Crea hr.advance tipo 'quincena' y lo desembolsa (account.payment)."""
        Advance = self.env['hr.advance'].sudo()

        adv_vals = {
            'employee_id': employee.id,
            'date': self.quincena_date,
            'amount': vals['neto'],
            'description': _('Quincena %s - %s') % (self.quincena_date, employee.name),
            'journal_id': self.journal_id.id,
            'advance_account_id': self.advance_account_id.id,
            'advance_type': 'quincena',
            'quincena_date': self.quincena_date,
            'quincena_dias_disponibles': vals['dias_disp'],
            'quincena_wage': vals['wage'],
            'quincena_monto_bruto': vals['bruto'],
            'quincena_monto_ips': vals['ips'],
            'quincena_monto_extraordinarios': vals['extras'],
            'quincena_monto_cuotas_prestamo': vals['deduccion_cuotas'],
            'quincena_monto_recupero_beneficio': vals['recupero_beneficio'],
        }
        advance = Advance.create(adv_vals)

        # Aprobar y desembolsar sin pasar por los checks de grupo
        advance.write({'state': 'rrhh_approved', 'rrhh_approver_id': self.env.user.id})
        advance._create_payment_and_attachment()

        # Absorber todos los pendientes (desembolsos Y recuperos)
        if vals['pending_loans']:
            vals['pending_loans'].write({
                'pending_in_quincena': False,
                'quincena_advance_id': advance.id,
            })
        return advance

    def _build_audit_message(self, employee, vals):
        return _(
            "<b>Quincena calculada</b><br/>"
            "Empleado: %s<br/>"
            "Bruto contrato: %s<br/>"
            "Dias disponibles: %d / 15 (proporcion %.4f)<br/>"
            "+ Bruto quincena (50%%): %s<br/>"
            "- IPS quincena (50%% del 9%%): %s<br/>"
            "- Recupero 1ra cuota beneficios pendientes (50%%): %s<br/>"
            "- Cuotas beneficios activos (50%%): %s<br/>"
            "<b>= Neto quincena: %s</b>"
        ) % (
            employee.name, vals['wage'],
            vals['dias_disp'], vals['proporcion'],
            vals['bruto'], vals['ips'],
            vals['recupero_beneficio'],
            vals['deduccion_cuotas'], vals['neto'],
        )
