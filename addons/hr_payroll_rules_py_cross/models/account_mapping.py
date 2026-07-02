# -*- coding: utf-8 -*-
"""Auto-creacion del Plan de Cuentas Paraguay (Resolucion 49/14 SET) y
mapeo a las reglas salariales."""
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


ACCOUNTS_PY_PAYROLL = [
    ('1.1.4.01', 'Anticipos al Personal',         'asset_current',     True),
    ('1.1.4.02', 'Prestamos al Personal',         'asset_current',     True),
    ('2.1.1.01', 'Sueldos a Pagar',               'liability_current', True),
    ('2.1.1.05', 'Vacaciones a Pagar',            'liability_current', True),
    ('2.1.1.06', 'Aguinaldo a Pagar',             'liability_current', True),
    ('2.1.1.07', 'Embargos a Depositar',          'liability_current', True),
    ('2.1.1.08', 'Otras Deducciones del Personal', 'liability_current', True),
    ('2.1.2.01', 'IPS Trabajador a Depositar',    'liability_current', True),
    ('2.1.2.02', 'IPS Patronal a Depositar',      'liability_current', True),
    ('5.1.1.01', 'Sueldos y Jornales',            'expense',           False),
    ('5.1.1.02', 'Bonificaciones',                'expense',           False),
    ('5.1.1.03', 'Vacaciones (Gasto)',            'expense',           False),
    ('5.1.1.04', 'Aguinaldo (Gasto)',             'expense',           False),
    ('5.1.1.05', 'Horas Extras',                  'expense',           False),
    ('5.1.1.06', 'Aporte Patronal IPS',           'expense',           False),
    ('5.1.1.07', 'Comisiones',                    'expense',           False),
    ('5.1.1.08', 'Bonificacion Feriado Trabajado', 'expense',          False),
]


RULE_ACCOUNT_MAP = [
    ('CN_SALARIO_BRUTO',  '5.1.1.01', '2.1.1.01'),
    ('BNR',               '5.1.1.02', '2.1.1.01'),
    ('BNEX',              '5.1.1.02', '2.1.1.01'),
    ('CP',                '5.1.1.07', '2.1.1.01'),
    ('BNFM',              '5.1.1.02', '2.1.1.01'),
    ('CN_VACACIONES',     '5.1.1.03', '2.1.1.05'),
    ('CN_AGUINALDO',      '5.1.1.04', '2.1.1.06'),
    ('CN_HE_DIA',         '5.1.1.05', '2.1.1.01'),
    ('CN_HE_NOCHE',       '5.1.1.05', '2.1.1.01'),
    ('CN_FERIADO_DIA',    '5.1.1.08', '2.1.1.01'),
    ('CN_FERIADO_NOCHE',  '5.1.1.08', '2.1.1.01'),
    ('PY_FERIADO_DIA',    '5.1.1.08', '2.1.1.01'),
    ('PY_FERIADO_NOCHE',  '5.1.1.08', '2.1.1.01'),
    ('PY_FERIADO_NOC',    '5.1.1.08', '2.1.1.01'),
    ('CN_IPS_TRAB',       '2.1.1.01', '2.1.2.01'),
    ('CN_FALTAS',         '2.1.1.01', '5.1.1.01'),
    ('PY_DESC_NO_REM',    '2.1.1.01', '5.1.1.01'),
    ('CN_ANTICIPO',       '2.1.1.01', '1.1.4.01'),
    ('CN_ANTICIPO_EXTRA', '2.1.1.01', '1.1.4.01'),
    ('CN_PRESTAMO',       '2.1.1.01', '1.1.4.02'),
    ('CN_EMBARGO',        '2.1.1.01', '2.1.1.07'),
    ('CN_OTROS_DESC',     '2.1.1.01', '2.1.1.08'),
    ('CN_IPS_PATRONAL',   '5.1.1.06', '2.1.2.02'),
    ('CN_SALARIO_NETO',   False,      '2.1.1.01'),
    ('NET',               False,      '2.1.1.01'),
]


RULES_TO_CLEAR_ACCOUNTS = [
    'CN_INGRESO_TOTAL',
]


def _ensure_payroll_accounts(env, companies=None):
    Account = env['account.account'].sudo()
    Company = env['res.company'].sudo()
    if not companies:
        companies = Company.search([])
    elif not hasattr(companies, '_name'):
        companies = Company.browse([c.id for c in companies])
    created = []
    for comp in companies:
        for code, name, atype, reconcile in ACCOUNTS_PY_PAYROLL:
            existing = Account.search([
                ('code', '=', code),
                ('company_ids', 'in', [comp.id]),
            ], limit=1)
            if existing:
                if reconcile and not existing.reconcile:
                    try:
                        existing.write({'reconcile': True})
                    except Exception as e:
                        _logger.warning('No se pudo marcar reconcile en %s: %s', code, e)
                continue
            try:
                vals = {
                    'code': code,
                    'name': name,
                    'account_type': atype,
                    'company_ids': [(6, 0, [comp.id])],
                }
                if reconcile:
                    vals['reconcile'] = True
                acc = Account.create(vals)
                created.append(acc)
                _logger.info('Cuenta creada %s - %s en %s', code, name, comp.name)
            except Exception as e:
                _logger.warning('No se pudo crear cuenta %s: %s', code, e)
    return created


def _map_accounts_to_rules(env, struct_ids=None):
    Rule = env['hr.salary.rule'].sudo()
    Account = env['account.account'].sudo()
    GLOBAL_RULE_CODES = ('NET',)
    mapped = 0
    skipped = 0
    for rule_code in RULES_TO_CLEAR_ACCOUNTS:
        rules_clear = Rule.with_context(active_test=False).search([
            ('code', '=', rule_code)
        ])
        for rule in rules_clear:
            vals_clear = {}
            if 'account_debit' in rule._fields and rule.account_debit:
                vals_clear['account_debit'] = False
            if 'account_credit' in rule._fields and rule.account_credit:
                vals_clear['account_credit'] = False
            if vals_clear:
                try:
                    rule.write(vals_clear)
                    _logger.info('Cuentas limpiadas en regla %s', rule_code)
                except Exception as e:
                    _logger.warning('No se pudo limpiar cuentas en %s: %s', rule_code, e)
    for rule_code, debit_code, credit_code in RULE_ACCOUNT_MAP:
        domain = [('code', '=', rule_code)]
        if struct_ids and rule_code not in GLOBAL_RULE_CODES:
            domain.append(('struct_id', 'in', struct_ids))
        rules = Rule.with_context(active_test=False).search(domain)
        if not rules:
            continue
        for rule in rules:
            company = env.company
            struct = rule.struct_id
            if struct and 'company_id' in struct._fields and struct.company_id:
                company = struct.company_id
            debit = False
            if debit_code:
                debit = Account.search([
                    ('code', '=', debit_code),
                    ('company_ids', 'in', [company.id]),
                ], limit=1)
            credit = False
            if credit_code:
                credit = Account.search([
                    ('code', '=', credit_code),
                    ('company_ids', 'in', [company.id]),
                ], limit=1)
            vals = {}
            if debit and 'account_debit' in rule._fields:
                vals['account_debit'] = debit.id
            elif not debit_code and 'account_debit' in rule._fields:
                vals['account_debit'] = False
            if credit and 'account_credit' in rule._fields:
                vals['account_credit'] = credit.id
            elif not credit_code and 'account_credit' in rule._fields:
                vals['account_credit'] = False
            if vals:
                try:
                    rule.write(vals)
                    mapped += 1
                except Exception as e:
                    _logger.warning('No se pudo mapear regla %s: %s', rule_code, e)
                    skipped += 1
            else:
                skipped += 1
    return mapped, skipped


def _ensure_payroll_journal(env, companies=None):
    Account = env['account.account'].sudo()
    Journal = env['account.journal'].sudo()
    Company = env['res.company'].sudo()
    if not companies:
        companies = Company.search([])
    elif not hasattr(companies, '_name'):
        companies = Company.browse([c.id for c in companies])
    configured = 0
    for comp in companies:
        journal = Journal.search([
            '|', '|', '|',
            ('name', 'ilike', 'salario'),
            ('name', 'ilike', 'payroll'),
            ('name', 'ilike', 'nomina'),
            ('code', '=', 'SLR'),
            ('company_id', '=', comp.id),
        ], limit=1)
        default_acc = Account.search([
            ('code', '=', '5.1.1.01'),
            ('company_ids', 'in', [comp.id]),
        ], limit=1)
        if not journal:
            try:
                vals = {
                    'name': 'Salarios',
                    'code': 'SLR',
                    'type': 'general',
                    'company_id': comp.id,
                }
                if default_acc:
                    vals['default_account_id'] = default_acc.id
                journal = Journal.create(vals)
                _logger.info('Diario Salarios creado en %s', comp.name)
                configured += 1
            except Exception as e:
                _logger.warning('No se pudo crear diario Salarios en %s: %s', comp.name, e)
        elif default_acc and not journal.default_account_id:
            try:
                journal.write({'default_account_id': default_acc.id})
                _logger.info('default_account_id seteada en diario %s', journal.name)
                configured += 1
            except Exception as e:
                _logger.warning('No se pudo setear default_account_id: %s', e)
    return configured


def _assign_journal_to_structures(env, struct_ids=None):
    Struct = env['hr.payroll.structure'].sudo()
    Journal = env['account.journal'].sudo()
    domain = []
    if struct_ids:
        domain = [('id', 'in', struct_ids)]
    structs = Struct.search(domain)
    assigned = 0
    for struct in structs:
        if 'journal_id' not in struct._fields:
            continue
        if struct.journal_id:
            continue
        company = env.company
        if 'company_id' in struct._fields and struct.company_id:
            company = struct.company_id
        journal = Journal.search([
            '|', '|',
            ('name', 'ilike', 'salario'),
            ('name', 'ilike', 'payroll'),
            ('code', '=', 'SLR'),
            ('company_id', '=', company.id),
        ], limit=1)
        if journal:
            try:
                struct.write({'journal_id': journal.id})
                assigned += 1
            except Exception as e:
                _logger.warning('No se pudo asignar diario a estructura %s: %s', struct.name, e)
    return assigned


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def action_setup_py_accounts(self):
        if not self:
            raise UserError(_('Seleccione al menos una estructura.'))
        companies = self.env['res.company']
        if 'company_id' in self._fields:
            companies = self.mapped('company_id').filtered(lambda c: c)
        if not companies:
            companies = self.env.company
        created = _ensure_payroll_accounts(self.env, companies)
        mapped, skipped = _map_accounts_to_rules(self.env, struct_ids=self.ids)
        journals = _ensure_payroll_journal(self.env, companies)
        struct_assigned = _assign_journal_to_structures(self.env, struct_ids=self.ids)
        msg = (
            'Plan de Cuentas Paraguay (Res. 49/14) configurado.\n'
            '- Cuentas creadas/verificadas: %d\n'
            '- Reglas mapeadas: %d (omitidas: %d)\n'
            '- Diarios configurados: %d\n'
            '- Estructuras con diario asignado: %d\n'
            'Cuentas de pasivo marcadas como CONCILIABLES.'
        ) % (len(created), mapped, skipped, journals, struct_assigned)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Plan de Cuentas PY'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            },
        }
