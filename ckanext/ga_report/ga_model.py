import re
import uuid

from sqlalchemy import Table, Column, MetaData, ForeignKey
from sqlalchemy import types
from sqlalchemy.sql import select
from sqlalchemy.orm import mapper, relation
from sqlalchemy import func

import ckan.model as model
from ckan.lib.base import *

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()

class GA_Url(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

url_table = Table('ga_url', metadata,
                      Column('id', types.UnicodeText, primary_key=True,
                             default=make_uuid),
                      Column('period_name', types.UnicodeText),
                      Column('period_complete_day', types.Integer),
                      Column('pageviews', types.UnicodeText),
                      Column('visitors', types.UnicodeText),
                      Column('url', types.UnicodeText),
                      Column('department_id', types.UnicodeText),
                      Column('package_id', types.UnicodeText),
                )
mapper(GA_Url, url_table)


class GA_Stat(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

stat_table = Table('ga_stat', metadata,
                  Column('id', types.UnicodeText, primary_key=True,
                         default=make_uuid),
                  Column('period_name', types.UnicodeText),
                  Column('stat_name', types.UnicodeText),
                  Column('key', types.UnicodeText),
                  Column('value', types.UnicodeText), )
mapper(GA_Stat, stat_table)


class GA_Publisher(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

pub_table = Table('ga_publisher', metadata,
                  Column('id', types.UnicodeText, primary_key=True,
                         default=make_uuid),
                  Column('period_name', types.UnicodeText),
                  Column('publisher_name', types.UnicodeText),
                  Column('views', types.UnicodeText),
                  Column('visitors', types.UnicodeText),
                  Column('toplevel', types.Boolean, default=False),
                  Column('subpublishercount', types.Integer, default=0),
                  Column('parent', types.UnicodeText),
)
mapper(GA_Publisher, pub_table)


class GA_ReferralStat(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

referrer_table = Table('ga_referrer', metadata,
                      Column('id', types.UnicodeText, primary_key=True,
                             default=make_uuid),
                      Column('period_name', types.UnicodeText),
                      Column('source', types.UnicodeText),
                      Column('url', types.UnicodeText),
                      Column('count', types.Integer),
                )
mapper(GA_ReferralStat, referrer_table)



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
    # Deliberately leaving a /
    url = url.replace('http:/','')
    return '/' + '/'.join(url.split('/')[2:])


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
    for url, views, visitors in url_data:
        url = _normalize_url(url)
        department_id = _get_department_id_of_url(url)

        package = None
        if url.startswith('/dataset/'):
            package = url[len('/dataset/'):]

        # see if the row for this url & month is in the table already
        item = model.Session.query(GA_Url).\
            filter(GA_Url.period_name==period_name).\
            filter(GA_Url.url==url).first()
        if item:
            item.period_name = period_name
            item.pageviews = views
            item.visitors = visitors
            item.department_id = department_id
            item.package_id = package
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                      'period_name': period_name,
                      'period_complete_day': period_complete_day,
                      'url': url,
                      'pageviews': views,
                      'visitors': visitors,
                      'department_id': department_id,
                      'package_id': package
                     }
            model.Session.add(GA_Url(**values))

        # We now need to recaculate the ALL time_period from the data we have
        # Delete the old 'All'
        old = model.Session.query(GA_Url).\
            filter(GA_Url.period_name == "All").\
            filter(GA_Url.url==url).delete()

        items = model.Session.query(GA_Url).\
            filter(GA_Url.period_name != "All").\
            filter(GA_Url.url==url).all()
        values = {'id': make_uuid(),
                  'period_name': "All",
                  'period_complete_day': "0",
                  'url': url,
                  'pageviews': sum([int(x.pageviews) for x in items]),
                  'visitors': sum([int(x.visitors) for x in items]),
                  'department_id': department_id,
                  'package_id': package
                 }
        model.Session.add(GA_Url(**values))

        model.Session.commit()


def update_social(period_name, data):
    # Clean up first.
    model.Session.query(GA_ReferralStat).\
        filter(GA_ReferralStat.period_name==period_name).delete()

    for url,data in data.iteritems():
        for entry in data:
            source = entry[0]
            count = entry[1]

            item = model.Session.query(GA_ReferralStat).\
                filter(GA_ReferralStat.period_name==period_name).\
                filter(GA_ReferralStat.source==source).\
                filter(GA_ReferralStat.url==url).first()
            if item:
                item.count = item.count + count
                model.Session.add(item)
            else:
                # create the row
                values = {'id': make_uuid(),
                          'period_name': period_name,
                          'source': source,
                          'url': url,
                          'count': count,
                         }
                model.Session.add(GA_ReferralStat(**values))
            model.Session.commit()

def update_publisher_stats(period_name):
    """
    Updates the publisher stats from the data retrieved for /dataset/*
    and /publisher/*. Will run against each dataset and generates the
    totals for the entire tree beneath each publisher.
    """
    toplevel = get_top_level()
    publishers = model.Session.query(model.Group).\
        filter(model.Group.type=='publisher').\
        filter(model.Group.state=='active').all()
    for publisher in publishers:
        views, visitors, subpub = update_publisher(period_name, publisher, publisher.name)
        parent, parents = '', publisher.get_groups('publisher')
        if parents:
            parent = parents[0].name
        item = model.Session.query(GA_Publisher).\
            filter(GA_Publisher.period_name==period_name).\
            filter(GA_Publisher.publisher_name==publisher.name).first()
        if item:
            item.views = views
            item.visitors = visitors
            item.publisher_name = publisher.name
            item.toplevel = publisher in toplevel
            item.subpublishercount = subpub
            item.parent = parent
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                     'period_name': period_name,
                     'publisher_name': publisher.name,
                     'views': views,
                     'visitors': visitors,
                     'toplevel': publisher in toplevel,
                     'subpublishercount': subpub,
                     'parent': parent
                     }
            model.Session.add(GA_Publisher(**values))
        model.Session.commit()


def update_publisher(period_name, pub, part=''):
    views,visitors,subpub = 0, 0, 0
    for publisher in go_down_tree(pub):
        subpub = subpub + 1
        items = model.Session.query(GA_Url).\
                filter(GA_Url.period_name==period_name).\
                filter(GA_Url.department_id==publisher.name).all()
        for item in items:
            views = views + int(item.pageviews)
            visitors = visitors + int(item.visitors)

    return views, visitors, (subpub-1)


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

def delete(period_name):
    '''
    Deletes table data for the specified period, or specify 'all'
    for all periods.
    '''
    for object_type in (GA_Url, GA_Stat, GA_Publisher, GA_ReferralStat):
        q = model.Session.query(object_type)
        if period_name != 'all':
            q = q.filter_by(period_name=period_name)
        q.delete()
    model.Session.commit()
