import logging
import ckan.lib.helpers as h
import ckan.plugins as p
from ckan.plugins import toolkit

from ckanext.ga_report.helpers import (most_popular_datasets,
                                       popular_datasets,
                                       single_popular_dataset,
                                       month_option_title,
                                       join_x, join_y)
try:
    from ckanext.report.interfaces import IReport
except ImportError:
    # if you've not install ckanext-report then you just find you can't use the report.
    IReport = p.ITemplateHelpers

log = logging.getLogger('ckanext.ga-report')


class GAReportPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)
    p.implements(IReport)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def get_helpers(self):
        """
        A dictionary of extra helpers that will be available to provide
        ga report info to templates.
        """
        return {
            'ga_report_installed': lambda: True,
            'popular_datasets': popular_datasets,
            'most_popular_datasets': most_popular_datasets,
            'single_popular_dataset': single_popular_dataset,
            'month_option_title': month_option_title,
            'join_x': join_x,
            'join_y': join_y,
        }

    def after_map(self, map):
        # GaReport
        map.connect(
            '/data/site-usage',
            controller='ckanext.ga_report.controller:GaReport',
            action='index'
        )
        map.connect(
            '/data/site-usage/data_{month}.csv',
            controller='ckanext.ga_report.controller:GaReport',
            action='csv'
        )
        map.connect(
            '/data/site-usage/downloads',
            controller='ckanext.ga_report.controller:GaReport',
            action='downloads'
        )
        map.connect(
            '/data/site-usage/downloads_{month}.csv',
            controller='ckanext.ga_report.controller:GaReport',
            action='csv_downloads'
        )

        # GaDatasetReport
        map.connect(
            '/data/site-usage/publisher',
            controller='ckanext.ga_report.controller:GaDatasetReport',
            action='publishers'
        )
        map.connect(
            '/data/site-usage/publishers_{month}.csv',
            controller='ckanext.ga_report.controller:GaDatasetReport',
            action='publisher_csv'
        )
        map.connect(
            '/data/site-usage/dataset/datasets_{id}_{month}.csv',
            controller='ckanext.ga_report.controller:GaDatasetReport',
            action='dataset_csv'
        )
        map.connect(
            '/data/site-usage/dataset',
            controller='ckanext.ga_report.controller:GaDatasetReport',
            action='read'
        )
        map.connect(
            '/data/site-usage/publisher/{id}',
            controller='ckanext.ga_report.controller:GaDatasetReport',
            action='read_publisher'
        )
        return map

    # IReport

    def register_reports(self):
        """Register details of an extension's reports"""
        from ckanext.ga_report import reports
        return [reports.publisher_report_info]
