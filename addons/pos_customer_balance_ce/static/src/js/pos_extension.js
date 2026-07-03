/** @odoo-module **/

import { PosGlobalState } from "@point_of_sale/app/store/pos_global_state";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, {
    // Note: In standard Odoo 18, fields should be added via the Python method _load_pos_data_fields.
    // We keep this patch as requested, but it might be redundant if the Python side is correctly implemented.
    async _loadData() {
        await super._loadData();
        if (this.add) {
            this.add('models.res.partner.fields', ['outstanding_debt', 'company_currency_id']);
        }
    },
});
