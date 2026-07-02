/** @odoo-module */

import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.transaction_reference = vals.transaction_reference || "";
    },
    set_transaction_reference(ref) {
        this.update({ transaction_reference: ref });
    },
    serialize(options = {}) {
        const result = super.serialize(...arguments);
        if (options.orm) {
            result.transaction_reference = this.transaction_reference;
        }
        return result;
    }
});
