/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.original_pricelist_id = this.original_pricelist_id || false;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.original_pricelist_id = json.original_pricelist_id;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.original_pricelist_id = this.original_pricelist_id ? this.original_pricelist_id.id || this.original_pricelist_id : false;
        return json;
    },
    addPaymentline(payment_method) {
        if (payment_method && payment_method.pricelist_id) {
            let pricelist = null;
            if (this.models && this.models['product.pricelist']) {
                const pricelists = this.models['product.pricelist'].getAll ? this.models['product.pricelist'].getAll() : this.models['product.pricelist'];
                
                let pl_id = payment_method.pricelist_id;
                if (Array.isArray(pl_id)) {
                    pl_id = pl_id[0];
                } else if (typeof pl_id === 'object') {
                    pl_id = pl_id.id;
                }
                
                pricelist = pricelists.find(p => p.id === pl_id);
            }
            
            if (pricelist) {
                // Save original pricelist to revert if needed
                if (!this.original_pricelist_id) {
                    this.original_pricelist_id = this.pricelist_id ? this.pricelist_id.id : (this.config.pricelist_id ? this.config.pricelist_id.id : false);
                }
                this.setPricelist(pricelist);
            }
        }
        return super.addPaymentline(payment_method);
    },
    removePaymentline(line) {
        const payment_method = line ? line.payment_method_id : null;
        const res = super.removePaymentline(line);
        
        if (payment_method && payment_method.pricelist_id) {
            // Revert pricelist if there are no other payment lines using this pricelist
            const remaining_paymentlines = this.payment_ids || [];
            const has_pricelist_method = remaining_paymentlines.some(l => {
                if (!l.payment_method_id || !l.payment_method_id.pricelist_id) return false;
                let l_pl_id = l.payment_method_id.pricelist_id;
                if (Array.isArray(l_pl_id)) l_pl_id = l_pl_id[0];
                else if (typeof l_pl_id === 'object') l_pl_id = l_pl_id.id;
                
                let pm_pl_id = payment_method.pricelist_id;
                if (Array.isArray(pm_pl_id)) pm_pl_id = pm_pl_id[0];
                else if (typeof pm_pl_id === 'object') pm_pl_id = pm_pl_id.id;
                
                return l_pl_id === pm_pl_id;
            });
            
            if (!has_pricelist_method && this.original_pricelist_id) {
                let original_pricelist = null;
                if (this.models && this.models['product.pricelist']) {
                    const pricelists = this.models['product.pricelist'].getAll ? this.models['product.pricelist'].getAll() : this.models['product.pricelist'];
                    original_pricelist = pricelists.find(p => p.id === this.original_pricelist_id);
                }
                
                if (original_pricelist) {
                    this.setPricelist(original_pricelist);
                }
                this.original_pricelist_id = false;
            }
        }
        return res;
    }
});
