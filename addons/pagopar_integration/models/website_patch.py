# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    def _send_abandoned_cart_email(self):
        """
        Patch for missing _send_abandoned_cart_email method.
        
        This method should normally be provided by website_sale addon.
        If website_sale is not installed or has issues, this fallback
        prevents the scheduled action from crashing.
        """
        _logger.warning(
            "website._send_abandoned_cart_email() called but method is missing from website_sale. "
            "This is a fallback implementation that does nothing. "
            "Please ensure website_sale addon is properly installed and updated."
        )
        return True 