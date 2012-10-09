import re
import uuid

from sqlalchemy import Table, Column, MetaData
from sqlalchemy import types
from sqlalchemy.sql import select
from sqlalchemy import func

import ckan.model as model
from ckan.model.types import JsonType
from ckan.lib.base import *


def make_uuid():
    return unicode(uuid.uuid4())


def init_tables():
    metadata = MetaData()
    package_stats = Table('ga_url', metadata,
                          Column('id', types.UnicodeText, primary_key=True,
                                 default=make_uuid),
                          Column('period_name', types.UnicodeText),
                          Column('period_complete_day', types.Integer),
                          Column('visits', types.Integer),
                          Column('group_id', types.String(60)),
                          Column('next_page', JsonType),
                          )
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
                return publisher_groups[0].id


def update_url_stats(period_name, period_complete_day, url_data):
    table = get_table('ga_url')
    connection = model.Session.connection()
    for url, views, next_page in url_data:
        url = _normalize_url(url)
        department_id = _get_department_id_of_url(url)
        # see if the row for this url & month is in the table already
        s = select([func.count(id_col)],
                   table.c.period_name == period_name,
                   table.c.url == url)
        count = connection.execute(s).fetchone()
        if count and count[0]:
            # update the row
            connection.execute(table.update()
                .where(table.c.period_name == period_name,
                       table.c.url == url)
                .values(period_complete_day=period_complete_day,
                        views=views,
                        department_id=department_id,
                        next_page=next_page))
        else:
            # create the row
            values = {'period_name': period_name,
                      'period_complete_day': period_complete_day,
                      'url': url,
                      'views': views,
                      'department_id': department_id,
                      'next_page': next_page}
            connection.execute(stats.insert().
                values(**values))
