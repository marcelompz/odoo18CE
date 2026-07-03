/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    get pos_orders() {
        return this.models['pos.order']?.getAll() || [];
    },
    get pos_order_lines() {
        return this.models['pos.order.line']?.getAll() || [];
    },

    createNewOrder() {
        const order = super.createNewOrder(...arguments);
        return order
        }
});


