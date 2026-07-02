/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { renderToElement } from "@web/core/utils/render"
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

import { Component, onRendered, useEffect, useRef, useState, onPatched } from "@odoo/owl";


patch(FormController.prototype, {
    setup() {
        super.setup()
        var self = this
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.uid = session.uid
        this.rec_id = this.modelParams.config.resId
        this.selected_product = []
        
        this.orm.call("shop.the.look", "get_html_data", [this.rec_id]).then((result) => {
            this.hotspot_data = result
        })
    },
    async onPagerUpdate({ offset, resIds }) {
        var self = this
        this.orm.call("shop.the.look", "get_html_data", [resIds[offset]]).then((result) => {
            if (result) {
                this.hotspot_data = result
            }
            else {
                this.hotspot_data = false
            }
        })
        this.rec_id = resIds[offset]
        super.onPagerUpdate(...arguments);
    },

    productSelectHotspot: function (evt) {
        var self = this;
        const $currentTarget = $(evt.target);
        let index = $currentTarget.closest('tr').index();
        var href = $currentTarget.val().trim();
        let pid = $currentTarget.find(":selected").attr('value')
        let line = $currentTarget.find(":selected").attr('line')
        if (!isNaN(pid)) {
            rpc('/get/product/info',{
                    'pid': pid
                },
            ).then(function (data) {
                data.href = href;
                data.line = line;
                self._updateMapArea(data, index);
            })
        } else {
            console.log('Something Went Wrong', pid);
        }
    },

    checkDuplicateProduct: function (ev) {
        var self = this
        self.selected_product = []
        $('.area-href').each(function (ev) {
            if ($.inArray($(this).val(), self.selected_product) === -1) {
                $('.save_hotspot').removeAttr('disabled')
                $('#duplicate_error').empty()
                self.selected_product.push($(this).val())
            }
            else {
                $('#duplicate_error').html(`<div class="alert alert-danger alert-dismissible" role="alert">
                <div>Duplicate items are not allowed.</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
           </div>`)
                $('.save_hotspot').attr('disabled', 'disabled')
                return false
            }
        });
    },

    async addHotspotButtonClicked(params = {}) {
        var self = this;
        const resId = this.props.resId;
        const res = await this.orm.call('shop.the.look','get_details',[this.rec_id]);

        const hotspotModal = renderToElement('shop_the_look.hotspotmodal', { res });
        this.$media = $(hotspotModal).find('.card-img-primary')
        this.mapId = this.$media.attr('usemap');
        this.src = this.$media.attr('src');
        this.width = $('.card-img-primary').width()
        this.height = $('.card-img-primary').height()
        this.$imageMaps = $(hotspotModal).find('.imagemaps-wrapper')
        this.imageMaps = $(hotspotModal).find('.imagemaps').html();
        $('.o_action_manager').find('.add_hotspot_modal').remove()
        $('.o_action_manager').append(hotspotModal)
        $('.add_hotspot_modal').modal("show")
        $('.add_hotspot_modal').on('change', this.productSelectHotspot.bind(this));
        $('.save_hotspot').on('click', this.save.bind(this));
        if (self.hotspot_data) {
            $(hotspotModal).find('.imagemaps-wrapper').empty()
            this.imageMaps = $(hotspotModal).find('.imagemaps-wrapper').html(self.hotspot_data)
        }
        if (this.imageMaps != undefined) {
            var $areas = self.$imageMaps.find('area');
            $areas = self._filterRemovedMapAreas($areas);
            self._reCalculateClassNames($areas);
        }
        this.ui.block("Loading...")
        setTimeout(function () {
            $('.imagemaps-wrapper').imageMaps({
                addBtn: '.btn-add-map',
                output: '.imagemaps-output',
                stopCallBack: function (active, coords) {
                    var position = active.position();
                    var percentLeft = position.left / $('.card-img-primary').width() * 100;
                    var percentRight = percentLeft + active.outerWidth() / $('.card-img-primary').width() * 100;
                    var percentTop = position.top / $('.card-img-primary').height() * 100;
                    var percentBottom = percentTop + active.outerHeight() / $('.card-img-primary').height() * 100;
                    let index = $(active[0]).index() - 2;// -2 for other 2 child inside imagemaps-wrapper
                    coords = {
                        'left': percentLeft,
                        'top': percentTop,
                        'right': percentRight,
                        'bottom': percentBottom,
                    }
                    self._updateMapArea(false, index, false, coords);
                }
            });
            $(document).on('click', '.btn-delete', self.checkDuplicateProduct.bind(this));
        }, 300);
        this.ui.unblock()
    },

    _filterRemovedMapAreas: function ($areas) {
        $areas.each(function () {
            if ($(this).hasClass('d-none')) {
                $(this).remove();
            }
        });
        return $areas;
    },

    _reCalculateClassNames: function ($areas) {
        let count = 0;
        $areas.each(function () {
            //TODO: Need tp be cross checked
            if (!$(this).hasClass('d-none')) {
                $(this).removeClass().addClass(`imagemaps-area${count}`);
                count++;
            }
        });
    },

    _generateHtml: function ($map) {
        return $map.html();
    },

    _updateMapArea: function (data, index, target = false, coords = false) {
        let $specificAreaTag = $('area#imagemaps-area').eq(index);
        var self = this
        self.checkDuplicateProduct()
        if (target) {
            $specificAreaTag.attr('target', target);
            return;
        }
        if (coords) {
            $specificAreaTag.attr('data-position', `{"left":"${coords.left}","top":"${coords.top}", "right":"${coords.right}", "bottom":"${coords.bottom}"}`);
            return;
        }
        $specificAreaTag.attr('data-content', JSON.stringify(data));
        $specificAreaTag.attr('href', data.href.trim());
    },

    _makeHotspotImages: function (content, x, y, display) {
        return `<img class="img_hotspot ${display}" src="/shop_the_look/static/src/images/hotspot_icon.svg" style="top: ${x}%; left: ${y}%;" data-custom-content='{"img": "${content.image}", "name": "${content.name}", "href": "${content.href}", "target": "${content.target}", "product_id": "${content.product_id}", "product_variant_id": "${content.product_variant_id}"}' alt="Hotspot"/>`;
    },

    pre_save_work: function () {
        var self = this;
        let hotspotImg, content, posContent, display;
        const $map_area = $('area#imagemaps-area');
        // if (!$('#hotspots_img').length) {
        //   $('map.imagemaps').after('<div id="hotspots_img"></div>');
        // }
        $('map.imagemaps').after('<div id="hotspots_img"></div>');
        $map_area.each(async function () {
            content = JSON.parse($(this).attr('data-content'));
            posContent = JSON.parse($(this).attr('data-position'));
            var target = $(this).attr('target');
            content.target = target;
            display = $(this).hasClass('d-none') ? 'd-none' : '';
            var topp = parseFloat(posContent.top);
            var bottom = parseFloat(posContent.bottom);
            var left = parseFloat(posContent.left);
            var right = parseFloat(posContent.right);
            var x = (topp + bottom) / 2;
            var y = (left + right) / 2;

            const position = await self.orm.call('shop.the.look','set_hotspot_position',[0],{
                    'id': self.props.resId,
                    'position_x': x || 0,
                    'position_y': y || 0,
                    'target' : content.target,
                    'line': content.line,

                },
            );
            window.location.reload();
        });

    },

    save: async function (evt) {
        var self = this;
        var args = arguments;
        var _super = self._super;
        $("[id^='imagemaps-rect']").remove();
        var data = false
        if($(".imagemaps-wrapper").length > 0){
            data = `${$(".imagemaps-wrapper").html().replace(/\s+/g, ' ')}`
        }
        this.orm.call('shop.the.look','empty_hotspot_position',[0],{
                'id': self.rec_id,
            },
        );
        if (data){
            const html_data = this.orm.call('shop.the.look','set_html_data',[0],{
                    'data': data,
                    'res_id': self.rec_id
                },
            )
        }
        if (!self.is_processing) {
            var args = arguments;
            const $currentTarget = $(evt.currentTarget);
            this.ui.block("Saving...");
            setTimeout(function () {
                self.pre_save_work();
                var href = $currentTarget.closest('tr').find('.area-href').val();
            }, 500);
            this.ui.unblock();
        }
        const record = this.model.root;
        let saved = false;
        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, evt);
        } else {
            saved = await record.save(evt);
        }
        if (saved && this.props.onSave) {
            this.props.onSave(record, evt);
        }
        return saved;
    }

});

