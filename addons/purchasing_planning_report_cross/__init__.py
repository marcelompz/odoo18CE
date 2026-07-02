from . import models

def post_init_hook(env):
    env['report.purchase.data.consolidated'].action_refresh_report()
