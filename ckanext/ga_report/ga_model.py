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

class GA_Stat(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

class GA_Publisher(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)


metadata = MetaData()
url_table = Table('ga_url', metadata,
                      Column('id', types.UnicodeText, primary_key=True,
                             default=make_uuid),
                      Column('period_name', types.UnicodeText),
                      Column('period_complete_day', types.Integer),
                      Column('pageviews', types.UnicodeText),
                      Column('visits', types.UnicodeText),
                      Column('url', types.UnicodeText),
                      Column('department_id', types.UnicodeText),
                )
mapper(GA_Url, url_table)

stat_table = Table('ga_stat', metadata,
                  Column('id', types.UnicodeText, primary_key=True,
                         default=make_uuid),
                  Column('period_name', types.UnicodeText),
                  Column('stat_name', types.UnicodeText),
                  Column('key', types.UnicodeText),
                  Column('value', types.UnicodeText), )
mapper(GA_Stat, stat_table)


pub_table = Table('ga_publisher', metadata,
                  Column('id', types.UnicodeText, primary_key=True,
                         default=make_uuid),
                  Column('period_name', types.UnicodeText),
                  Column('publisher_name', types.UnicodeText),
                  Column('views', types.UnicodeText),
                  Column('visits', types.UnicodeText),
)
mapper(GA_Publisher, pub_table)


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
    else:
        publisher_match = re.match('/publisher/([^/]+)(/.*)?', url)
        if publisher_match:
            return publisher_match.groups()[0]


def update_sitewide_stats(period_name, stat_name, data):
    for k,v in data.iteritems():
        item = model.Session.query(GA_Stat).\
            filter(GA_Stat.period_name==period_name).\
            filter(GA_Stat.key==k).\
            filter(GA_Stat.stat_name==stat_name).first()
        if item:
            item.period_name = period_name
            item.key = k
            item.value = v
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                     'period_name': period_name,
                     'key': k,
                     'value': v,
                     'stat_name': stat_name
                     }
            model.Session.add(GA_Stat(**values))
        model.Session.commit()



def update_url_stats(period_name, period_complete_day, url_data):
    for url, views, visits in url_data:
        url = _normalize_url(url)
        department_id = _get_department_id_of_url(url)

        # see if the row for this url & month is in the table already
        item = model.Session.query(GA_Url).\
            filter(GA_Url.period_name==period_name).\
            filter(GA_Url.url==url).first()
        if item:
            item.period_name = period_name
            item.pageviews = views
            item.visits = visits
            item.department_id = department_id
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                      'period_name': period_name,
                      'period_complete_day': period_complete_day,
                      'url': url,
                      'pageviews': views,
                      'visits': visits,
                      'department_id': department_id
                     }
            model.Session.add(GA_Url(**values))
        model.Session.commit()



def update_publisher_stats(period_name):
    publishers = get_top_level()
    for publisher in publishers:
        views, visits = update_publisher(period_name, publisher, publisher.name)
        item = model.Session.query(GA_Publisher).\
            filter(GA_Publisher.period_name==period_name).\
            filter(GA_Publisher.publisher_name==publisher.name).first()
        if item:
            item.views = views
            item.visits = visits
            item.publisher_name = publisher.name
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                     'period_name': period_name,
                     'publisher_name': publisher.name,
                     'views': views,
                     'visits': visits,
                     }
            model.Session.add(GA_Publisher(**values))
        model.Session.commit()


def update_publisher(period_name, pub, part=''):
    views,visits = 0, 0
    for publisher in go_down_tree(pub):
        f = model.Session.query(GA_Url).\
                filter(GA_Url.period_name==period_name).\
                filter(GA_Url.url=='/publisher/' + publisher.name).first()
        if f:
            views = views + int(f.pageviews)
            visits = visits + int(f.visits)

    return views, visits


def get_top_level():
    '''Returns the top level publishers.'''
    return model.Session.query(model.Group).\
           outerjoin(model.Member, model.Member.table_id == model.Group.id and \
                     model.Member.table_name == 'group' and \
                     model.Member.state == 'active').\
           filter(model.Member.id==None).\
           filter(model.Group.type=='publisher').\
           order_by(model.Group.name).all()

def get_children(publisher):
    '''Finds child publishers for the given publisher (object). (Not recursive)'''
    from ckan.model.group import HIERARCHY_CTE
    return model.Session.query(model.Group).\
           from_statement(HIERARCHY_CTE).params(id=publisher.id, type='publisher').\
           all()

def go_down_tree(publisher):
    '''Provided with a publisher object, it walks down the hierarchy and yields each publisher,
    including the one you supply.'''
    yield publisher
    for child in get_children(publisher):
        for grandchild in go_down_tree(child):
            yield grandchild
