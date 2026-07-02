# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2016-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################

{
  "name"                 :  "Shop The Look",
  "summary"              :  """
                              Enhance your shopping with Odoo's Shop the Look. Explore curated product sets, use the hotspot feature to magnify items on hover, and effortlessly purchase complementary products all in one place.
                            """,
  "category"             :  "Website",
  "version"              :  "1.0.1",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/odoo-website-shop-the-look.html",
  "description"          :  """
                              Explore Website Shop the Look for curated product sets, effortlessly elevating your style and home decor.
                              Shop now and complete your look! | Odoo website | Shop the Look | Curated products | Complete ensembles | Fashion combinations | Home decor sets | Seamless shopping | Elevated style | Product pairings | Fashion inspiration | Streamlined shopping | User-friendly experience | Enhanced user journey | Cross-selling opportunities | Upselling suggestions | Brand identity | Time-saving shopping | Odoo-style shopping | Style optimization | Customer satisfaction | Seasonal collections | Shopping convenience | Fashion trends | Home interior solutions | Odoo | Odoo admin | Odoo app | Odoo Website Shop the Look | Odoo apps | Website Shop the Look | hotspot | odoo website shop the look hotspot | odoo hotspot feature
                            """,
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=shop_the_look&custom_url=/",
  "depends"              :  [
                             'website_sale',
                            ],
  "data"                 :  [
                           "security/ir.model.access.csv",
                           "views/shop_the_look.xml",
                           "views/website_config_setting.xml",
                           'views/views.xml',
                           'views/menu.xml',
                            ],
  "demo"                 :  [
                              'demo/demo.xml'
                            ],

  'assets'               :{
                            'web.assets_frontend':[
                              'shop_the_look/static/src/fonts/*.woff2',
                              'shop_the_look/static/src/fonts/*.woff',
                              'shop_the_look/static/src/js/look_book.js',
                              'shop_the_look/static/src/js/script.js',
                              'shop_the_look/static/src/js/owl.carousel.js',
                              'shop_the_look/static/src/js/owl.carousel.min.js',
                              'shop_the_look/static/src/css/*.css',
                              'shop_the_look/static/src/css/*.scss',
                              'shop_the_look/static/src/scss/lookbook_list_views.scss'

                            ],
                            'web.assets_backend': [
                                "/web/static/lib/jquery/jquery.js",
                                "shop_the_look/static/lib/imagemap/jquery-ui.css",
                                "shop_the_look/static/lib/imagemap/jquery-ui.js",
                                "shop_the_look/static/lib/imagemap/jquery.imagemaps.js",
                                "shop_the_look/static/src/js/add_hotspot.js",
                                "shop_the_look/static/src/xml/add_hotspot_button.xml",
                                "shop_the_look/static/src/xml/add_hotspot.scss",
                            ],
                          },
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  169,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",

}
