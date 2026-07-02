/** @odoo-module **/
require("@website_sale/js/website_sale");
import publicWidget from "@web/legacy/js/public/public_widget";



publicWidget.registry.shopLook = publicWidget.Widget.extend({
  selector: '#slider',
  start: function () {
    this._super.apply(this, arguments)
    this._slick_carousel()
  },

  _slick_carousel: function () {
    const slider = $(".slider");
    slider
      .slick({
        vertical: true,
        infinite: false,
        arrows: true,
        dots: true,
        centerPadding: '0',
        verticalSwiping: true,
        centerMode: true,
      });

    slider.on('wheel', (function (e) {
      e.preventDefault();

      if (e.originalEvent.deltaY > 0) {
        $(this).slick('slickNext');
      } else {
        $(this).slick('slickPrev');
      }
    }));
  }


});

publicWidget.registry.shopTheLookOptions = publicWidget.Widget.extend({
  selector: '.shop_the_look_main ,.product_options_div',

  events: {
    // 'change #modal_qty': '_onChangeModalQty',
    // 'click #add_all': '_onAddAllBtn',
  },

  start: function () {
    this._super.apply(this, arguments)
    this._prod_options_carousel()
  },
  _prod_options_carousel: function () {
    $('.shop_look_carousel').owlCarousel({
      nav: true,
      margin: 10,

      responsive: {

        200: {
          items: 1,
        },
        600: {
          items: 2,
        },
        1000: {
          items: 3,

        }
      },
    })
  },




  // _onChangeModalQty: function () {
  //   var qty = parseInt($("#modal_qty").val());

  //   if (modal_qty <= 0) {
  //     $("#add_all").attr('disabled', 'disabled');
  //   }
  //   else {
  //     $("#add_all").prop("disabled", false);
  //   }
  // },





  // _onAddAllBtn: function () {
  //   const ids = [];
  //   var qty = parseInt($("#modal_qty").val());
  //   $(".items_to_add").each(function () {
  //     var id = $(this).find(":selected").val();
  //     ids.push(parseInt(id))
  //   });
  //   const uniq = [...new Set(ids)];
  //   try {
  //     if (ids && (qty > 0)) {
  //       $(this).prop("disabled", false);
  //       ajax.jsonRpc("/shop/look/cart/update", 'call', { "product_id": uniq, "add_qty": qty })
  //         .then(function (res) {
  //           window.location.reload();
  //         })
  //     }
  //     else {
  //       $(this).attr('disabled', 'disabled');
  //     }

  //   }
  //   catch (e) { }


  // },
});


publicWidget.registry.shopTheLookDetailPage = publicWidget.Widget.extend({
  selector: "#product_detail_main",
  events: {
    'change #prod_qty': '_onChangeProdQty',

  },

  start: function () {
    this._super.apply(this, arguments)
    this.look_detail_carousel()
  },
  look_detail_carousel: function () {
    $('.owl-carousel').owlCarousel({
      nav: true,
      loop: true,
      margin: 10,
      arrows: false,

      responsive: {

        200: {
          items: 1,
        },
        600: {
          items: 1,
        },
        1000: {
          items: 1,

        }
      },
    })

  },
  _onChangeProdQty: function () {
    var qty = parseInt($("#prod_qty").val());

    $("#modal_qty").val(qty)
    var modal_qty = parseInt($("#prod_qty").val());
    if (modal_qty <= 0) {
      $("#add_all").attr('disabled', 'disabled');
    }
    else {
      $("#add_all").prop("disabled", false);
    }


  },



});
