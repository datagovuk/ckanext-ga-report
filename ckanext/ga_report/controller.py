import logging
from ckan.lib.base import BaseController, c, render
import report_model

log = logging.getLogger('ckanext.ga-report')

class GaReport(BaseController):
    def index(self):
        return render('ga_report/site/index.html')


class GaPublisherReport(BaseController):

    def index(self, id):
        return render('ga_report/publisher/index.html')
