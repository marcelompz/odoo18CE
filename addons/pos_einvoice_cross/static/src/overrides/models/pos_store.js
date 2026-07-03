/** @odoo-module */

import {PosStore} from "@point_of_sale/app/services/pos_store";
import {patch} from "@web/core/utils/patch";

patch(PosStore.prototype, {
    get city_id() {
        return this.models['res.country.state.district.city']?.getAll() || [];
    },
    get l10n_latam_identification_type_id() {
        return this.models['l10n_latam.identification.type']?.getAll() || [];
    },
});
