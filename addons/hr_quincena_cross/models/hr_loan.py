# -*- coding: utf-8 -*-
"""Extension del Beneficio (hr.loan) con:
  - benefit_type_id (Many2one a hr.benefit.type) configurable por RRHH.
  - Validacion de antiguedad minima cuando el tipo lo requiere.
  - Inicio del descuento de cuotas el MES SIGUIENTE al desembolso.
  - Si el contrato del empleado tiene cn_paga_quincena=True, el desembolso
    NO genera account.payment inmediato; queda marcado como
    'pendiente_quincena' para ser absorbido por el proximo wizard de quincena.
  - Trazabilidad via quincena_advance_id (hr.advance que lo incluyo).

Nota: el modelo subyacente sigue siendo hr.loan (no se renombra para evitar
romper relaciones existentes), pero las etiquetas visibles ahora dicen
"Beneficio" en lugar de "Prestamo".
"""
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    benefit_type_id = fields.Many2one(
        'hr.benefit.type', string='Tipo de Beneficio',
        tracking=True, ondelete='restrict',
        help='Tipo de beneficio (Prestamo, Uniforme, Prestamo Emergencia, etc.). '
             'Cada tipo puede requerir antiguedad minima o no, y se fracciona '
             'por defecto o no, segun su configuracion.',
    )
    # Campo LEGACY: se mantiene por compatibilidad con vistas/registros previos
    # que pudieran haber sido instalados con la version anterior (Selection).
    # Se calcula desde benefit_type_id.code y no se almacena en BD.
    loan_type = fields.Selection(
        selection=[
            ('prestamo', 'Prestamo'),
            ('uniforme', 'Uniforme'),
            ('beneficio', 'Beneficio'),
            ('otros', 'Otros'),
            ('emergencia', 'Prestamo Emergencia'),
        ],
        string='Tipo (legacy)',
        compute='_compute_loan_type_legacy',
        store=False,
        help='DEPRECATED: usar benefit_type_id en su lugar. '
             'Se mantiene por compatibilidad con vistas instaladas previamente.',
    )

    @api.depends('benefit_type_id', 'benefit_type_id.code')
    def _compute_loan_type_legacy(self):
        """Mapea benefit_type_id.code -> loan_type (legacy Selection)."""
        mapping = {
            'PRESTAMO':   'prestamo',
            'UNIFORME':   'uniforme',
            'BENEFICIO':  'beneficio',
            'EMERGENCIA': 'emergencia',
            'OTROS':      'otros',
        }
        for rec in self:
            if rec.benefit_type_id:
                rec.loan_type = mapping.get(rec.benefit_type_id.code, 'otros')
            else:
                rec.loan_type = False
    is_fractional = fields.Boolean(
        string='Se fracciona en cuotas',
        compute='_compute_is_fractional', store=True, readonly=False,
        help='Si NO se fracciona, no se generan cuotas mensuales (pago unico, '
             'no se descuenta del salario).',
    )
    pending_in_quincena = fields.Boolean(
        string='Pendiente de incluir en quincena',
        default=False, copy=False, readonly=True,
        help='Indica que el desembolso esta pendiente de ser absorbido por el '
             'proximo anticipo quincenal del empleado.',
    )
    quincena_advance_id = fields.Many2one(
        'hr.advance', string='Quincena que lo incluyo',
        copy=False, readonly=True,
    )
    installment_first_date = fields.Date(
        string='1er descuento de cuota',
        compute='_compute_installment_first_date', store=True,
        help='Mes en que se empieza a descontar la primera cuota (1° dia del '
             'mes siguiente al desembolso).',
    )

    @api.onchange('benefit_type_id')
    def _onchange_benefit_type_id(self):
        """Al elegir el tipo, sugerir is_fractional y cantidad de cuotas."""
        if self.benefit_type_id:
            self.is_fractional = self.benefit_type_id.is_fractional_default
            if self.benefit_type_id.default_installments:
                self.installments = self.benefit_type_id.default_installments

    @api.depends('benefit_type_id')
    def _compute_is_fractional(self):
        for rec in self:
            if rec.benefit_type_id:
                rec.is_fractional = rec.benefit_type_id.is_fractional_default

    @api.depends('date_start')
    def _compute_installment_first_date(self):
        for rec in self:
            if not rec.date_start:
                rec.installment_first_date = False
                continue
            d = rec.date_start
            if d.month == 12:
                rec.installment_first_date = date(d.year + 1, 1, 1)
            else:
                rec.installment_first_date = date(d.year, d.month + 1, 1)

    # ------------------------------------------------------------------
    # Validacion de antiguedad (solo si el tipo lo requiere)
    # ------------------------------------------------------------------
    @api.constrains('benefit_type_id', 'employee_id', 'date_start')
    def _check_antiguedad(self):
        for rec in self:
            if not rec.benefit_type_id or not rec.benefit_type_id.requires_seniority:
                continue
            if not rec.employee_id:
                continue
            min_dias = rec.company_id.cn_antiguedad_minima_prestamo_dias or 0
            if min_dias <= 0:
                continue
            Contract = self.env['hr.contract']
            first_contract = Contract.search([
                ('employee_id', '=', rec.employee_id.id),
                ('date_start', '!=', False),
            ], order='date_start asc', limit=1)
            if not first_contract:
                raise UserError(_(
                    "El empleado '%s' no tiene contrato registrado. No se puede "
                    "validar la antiguedad para un beneficio tipo '%s'."
                ) % (rec.employee_id.name, rec.benefit_type_id.name))
            ref_date = rec.date_start or fields.Date.context_today(rec)
            antiguedad_dias = (ref_date - first_contract.date_start).days
            if antiguedad_dias < min_dias:
                raise UserError(_(
                    "El empleado '%s' tiene %d dias de antiguedad. Se requieren "
                    "minimo %d dias para un beneficio tipo '%s'. "
                    "Considere usar otro tipo que no requiera antiguedad."
                ) % (rec.employee_id.name, antiguedad_dias, min_dias,
                     rec.benefit_type_id.name))

    # ------------------------------------------------------------------
    # Override del desembolso
    # ------------------------------------------------------------------
    def _create_payment_and_attachment(self):
        """Override para soportar el flujo quincenal.

        Si el contrato del empleado tiene cn_paga_quincena=True:
            - NO se genera account.payment inmediato.
            - Se marca el beneficio como pending_in_quincena=True.
            - Se crea el hr.salary.attachment con date_start = 1° del mes
              siguiente (cuotas empiezan el mes siguiente).
        Si el contrato NO tiene cn_paga_quincena:
            - Comportamiento original (account.payment inmediato).
            - Pero la cuota igual empieza el mes siguiente.
        """
        self.ensure_one()
        contract = self.employee_id.contract_id if self.employee_id else False
        paga_quincena = bool(contract and getattr(contract, 'cn_paga_quincena', False))

        # Caso 1: pago inmediato
        if not paga_quincena:
            res = super()._create_payment_and_attachment()
            if self.salary_attachment_id and self.installment_first_date:
                self.salary_attachment_id.sudo().write({
                    'date_start': self.installment_first_date,
                })
            return res

        # Caso 2: pendiente de quincena
        tipo_label = self.benefit_type_id.name if self.benefit_type_id else 'Beneficio'

        if not self.is_fractional:
            # No fraccionable: pago unico, sin attachment
            self.write({
                'state': 'paid',
                'pending_in_quincena': True,
                'finance_approver_id': self.env.user.id,
            })
            self.message_post(body=_(
                'Beneficio "%s" desembolsado: %s. Pendiente de incluir en proxima quincena.'
            ) % (tipo_label, self.amount_total))
            return

        # Fraccionable: crear attachment para descuento mensual.
        # Para empleados con quincena: la cuota se divide 50/50 entre
        # quincena y nomina de fin de mes. El attachment cubre solo el 50% restante.
        Attachment = self.env['hr.salary.attachment'].sudo()
        desc = self.description or (_('%s - %s') % (tipo_label, self.name))
        input_type = self.env.ref(
            'hr_loan_advance_py_cross.hr_payslip_input_type_prestamo',
            raise_if_not_found=False,
        )
        if not input_type:
            raise UserError(_(
                'Falta el tipo de entrada de nomina "Cuota de Prestamo". '
                'Reinstale el modulo hr_loan_advance_py_cross.'
            ))
        attachment_monthly = self.amount_per_installment / 2.0
        attachment_total = self.amount_total / 2.0
        attachment_vals = {
            'description': desc,
            'monthly_amount': attachment_monthly,
            'total_amount': attachment_total,
            'date_start': self.installment_first_date or self.date_start,
            'state': 'open',
            'other_input_type_id': input_type.id,
        }
        if 'employee_ids' in Attachment._fields:
            attachment_vals['employee_ids'] = [(4, self.employee_id.id)]
        elif 'employee_id' in Attachment._fields:
            attachment_vals['employee_id'] = self.employee_id.id
        attachment = Attachment.create(attachment_vals)

        self.write({
            'state': 'paid',
            'pending_in_quincena': True,
            'salary_attachment_id': attachment.id,
            'finance_approver_id': self.env.user.id,
        })
        self.message_post(body=_(
            'Beneficio "%s" desembolsado: %s. Pendiente de incluir en proxima quincena. '
            'Cuotas mensuales a partir de %s.'
        ) % (tipo_label, self.amount_total, self.installment_first_date or '-'))

    # ------------------------------------------------------------------
    # Override del cancel
    # ------------------------------------------------------------------
    def action_cancel(self):
        for rec in self:
            if rec.quincena_advance_id:
                raise UserError(_(
                    "No se puede cancelar el beneficio '%s' porque ya fue "
                    "incluido en la quincena '%s'. Cancele primero la quincena."
                ) % (rec.name, rec.quincena_advance_id.name or ''))
        return super().action_cancel()
