import re
import uuid

from sqlalchemy import Table, Column, MetaData
from sqlalchemy import types
from sqlalchemy.sql import select
from sqlalchemy.orm import mapper
from sqlalchemy import func

import ckan.model as model
from ckan.lib.base import *

def make_uuid():
    return unicode(uuid.uuid4())



class GA_Url(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)


metadata = MetaData()
url_table = Table('ga_url', metadata,
                      Column('id', types.UnicodeText, primary_key=True,
                             default=make_uuid),
                      Column('period_name', types.UnicodeText),
                      Column('period_complete_day', types.Integer),
                      Column('metric', types.UnicodeText),
                      Column('value', types.UnicodeText),
                      Column('url', types.UnicodeText),
                      Column('department_id', types.UnicodeText),
                )
mapper(GA_Url, url_table)


def init_tables():
    metadata.create_all(model.meta.engine)


cached_tables = {}


def get_table(name):
    if name not in cached_tables:
        meta = MetaData()
        meta.reflect(bind=model.meta.engine)
        table = meta.tables[name]
        cached_tables[name] = table
    return cached_tables[name]


def _normalize_url(url):
    '''Strip off the hostname etc. Do this before storing it.

    >>> normalize_url('http://data.gov.uk/dataset/weekly_fuel_prices')
    '/dataset/weekly_fuel_prices'
    '''
    url = re.sub('https?://(www\.)?data.gov.uk', '', url)
    return url


def _get_department_id_of_url(url):
    # e.g. /dataset/fuel_prices
    # e.g. /dataset/fuel_prices/resource/e63380d4
    dataset_match = re.match('/dataset/([^/]+)(/.*)?', url)
    if dataset_match:
        dataset_ref = dataset_match.groups()[0]
        dataset = model.Package.get(dataset_ref)
        if dataset:
            publisher_groups = dataset.get_groups('publisher')
            if publisher_groups:
                return publisher_groups[0].name


def update_url_stats(period_name, period_complete_day, url_data):
    table = get_table('ga_url')
    for url, views, next_page in url_data:
        url = _normalize_url(url)
        department_id = _get_department_id_of_url(url)

        # see if the row for this url & month is in the table already
        item = model.Session.query(GA_Url).\
            filter(GA_Url.period_name==period_name).\
            filter(GA_Url.url==url).\
            filter(GA_Url.metric == 'Total views').first()
        if item:
            item.period_name = period_complete_day = period_complete_day
            item.value = views
            item.department_id = department_id
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                      'period_name': period_name,
                      'period_complete_day': period_complete_day,
                      'url': url,
                      'value': views,
                      'metric': 'Total views',
                      'department_id': department_id
                     }
            model.Session.add(GA_Url(**values))
        model.Session.commit()
