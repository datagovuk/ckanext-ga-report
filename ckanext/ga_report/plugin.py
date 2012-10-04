import logging
import ckan.lib.helpers as h
from ckan.plugins import implements, toolkit
import gasnippet
import commands
import dbutil

log = logging.getLogger('ckanext.ga-report')

class GoogleAnalyticsPlugin(p.SingletonPlugin):
    implements(p.IConfigurer, inherit=True)
    implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def after_map(self, map):
        map.connect(
            '/data/analytics/index',
            controller='ckanext.ga-report.controller:GaReport',
            action='index'
        )
        return map

