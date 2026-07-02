import logging
import json

from odoo.http import request, route
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class StockCardDetail(CustomerPortal):
    @route(
        ["/stock_card_detail/<int:wizard_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def stock_card_detail(self, wizard_id):
        _logger.info(f'\n wizard_id: {wizard_id}')
        values = self._prepare_portal_layout_values()
        wizard_id = request.env['ms.stock.report.wizard'].search([
            ('id', '=', wizard_id)
        ])
        values.update(
            {
                "wizard_id": wizard_id,
            }
        )
        return request.render(
            "ms_stock_report.stock_card_detail_template",
            values,
            headers={"X-Frame-Options": "DENY"},
        )
