import logging
import ckan.lib.helpers as h
import ckan.plugins as p
from ckan.plugins import implements, toolkit
#import gasnippet
#import commands
#import dbutil

log = logging.getLogger('ckanext.ga-report')

class GAReportPlugin(p.SingletonPlugin):
    implements(p.IConfigurer, inherit=True)
    implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def after_map(self, map):
        map.connect(
            '/data/analytics/publisher',
            controller='ckanext.ga_report.controller:GaPublisherReport',
            action='index'
        )
        map.connect(
            '/data/analytics/publisher/{id}',
            controller='ckanext.ga_report.controller:GaPublisherReport',
            action='read'
        )
        map.connect(
            '/data/analytics',
            controller='ckanext.ga_report.controller:GaReport',
            action='index'
        )
        map.connect(
            '/data/analytics/data_{month}.csv',
            controller='ckanext.ga_report.controller:GaReport',
            action='csv'
        )
        return map

