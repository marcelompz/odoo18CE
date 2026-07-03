# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 22:37:23

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('py')
    def _get_py_template_data(self):
        return {
            'name': _('Paraguay - Accounting'),
            'visible': True,
            'code_digits': '2',
            'property_account_receivable_id': 'cross_account_1010301',
            'property_account_payable_id': 'cross_account_2010101',
            'property_account_expense_categ_id': 'cross_account_501',
            'property_account_income_categ_id': 'cross_account_401',
            'property_stock_account_input_categ_id': 'cross_account_2010501',
            'property_stock_account_output_categ_id': 'cross_account_1020101',
            'property_stock_valuation_account_id': 'cross_account_1010401',
        }

    @template('py', 'res.company')
    def _get_py_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.py',
                'bank_account_code_prefix': '1101',
                'cash_account_code_prefix': '1101',
                'transfer_account_code_prefix': '117',
                'account_default_pos_receivable_account_id': 'cross_account_1010301',
                'income_currency_exchange_account_id': 'cross_account_805',
                'expense_currency_exchange_account_id': 'cross_account_805',
                'tax_calculation_rounding_method': 'round_globally',
                'account_sale_tax_id': 'ITAX_10',
                'account_purchase_tax_id': 'OTAX_10',
            },
        }
