/** @odoo-module */


import {patch} from "@web/core/utils/patch";
import {PartnerDetailsEdit} from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments)
        const partner = this.props.partner;
        this.changes.city_id = partner.city_id && partner.city_id[0];
        this.changes.l10n_latam_identification_type_id = partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0];
    },

    async saveChanges() {
        if (
            (!this.props.partner.city_id && !this.changes.city_id) ||
            this.changes.city_id === ""
        ) {
            this.changes.city_id = false;
        } else {
            const cityId = Array.isArray(this.changes.city_id)
                ? parseInt(this.changes.city_id[0])
                : parseInt(this.changes.city_id);
            this.changes.city_id = cityId ? cityId : false;
        }

        if (
            (!this.props.partner.l10n_latam_identification_type_id && !this.changes.l10n_latam_identification_type_id) ||
            this.changes.l10n_latam_identification_type_id === ""
        ) {
            this.changes.l10n_latam_identification_type_id = false;
        } else {
            const latamIdType = Array.isArray(this.changes.l10n_latam_identification_type_id)
                ? parseInt(this.changes.l10n_latam_identification_type_id[0])
                : parseInt(this.changes.l10n_latam_identification_type_id);
            this.changes.l10n_latam_identification_type_id = latamIdType ? latamIdType : false;
        }
    
        try {
            await super.saveChanges();
        } catch (error) {
            console.error("Error saving changes:", error);
        }
    }
})
