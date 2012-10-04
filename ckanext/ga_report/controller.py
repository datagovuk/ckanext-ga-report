import logging
from ckan.lib.base import BaseController, c, render
import report_model

log = logging.getLogger('ckanext.ga-report')

class GaReport(BaseController):
    def index(self):
        return render('index.html')
