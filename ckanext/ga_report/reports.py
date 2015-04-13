import collections
from itertools import groupby

from sqlalchemy import func

from ckan import model
from ckan.lib.helpers import OrderedDict
from ckanext.dgu.lib.publisher import go_up_tree
from ga_model import GA_Url  # , GA_Stat, GA_ReferralStat, GA_Publisher


def publisher_report(metric):
    orgs = dict(model.Session.query(model.Group.name, model.Group)\
                     .filter_by(state='active').all())

    org_counts = collections.defaultdict(dict)
    if metric in ('views', 'viewsdownloads', 'visits'):
        if metric == 'views' or metric == 'viewsdownloads':
            sql_function = 'sum(pageviews::int)'
        elif metric == 'visits':
            sql_function = 'sum(visits::int)'
        q = '''
            select department_id, period_name, %s metric
            from ga_url
            where department_id <> ''
            and package_id <> ''
            group by department_id, period_name
            order by department_id
        ''' % sql_function

        org_period_count = model.Session.connection().execute(q)

        for org_name, period_name, count in org_period_count:
            org_counts[org_name][period_name] = count

    if metric in ('downloads', 'viewsdownloads'):
        q = '''
            select g.name as org_name, s.period_name, sum(s.value::int) as downloads
            from GA_Stat as s
            join Package as p on s.key=p.name
            join "group" as g on p.owner_org=g.id
            where stat_name='Downloads'
            and g.state='active'
            group by org_name, s.period_name
            order by downloads desc;
            '''
        org_period_count = model.Session.connection().execute(q)

        if metric == 'viewsdownloads':
            # add it onto the existing counts
            for org_name, period_name, count in org_period_count:
                org_counts[org_name][period_name] = count + \
                    org_counts[org_name].get(period_name, 0)
                org_counts[org_name]['All'] = count + \
                    org_counts[org_name].get('All', 0)
        else:
            for org_name, period_name, count in org_period_count:
                org_counts[org_name][period_name] = count
                org_counts[org_name]['All'] = count + \
                    org_counts[org_name].get('All', 0)

    org_counts = sorted(org_counts.items(),
                        key=lambda x: -x[1].get('All', 0))

    all_periods = [
        res[0] for res in model.Session.query(GA_Url.period_name)
                               .group_by(GA_Url.period_name)
                               .order_by(GA_Url.period_name)
                               .all()]
    rows = []
    for org_name, counts in org_counts:
        org = orgs.get(org_name)
        if not org:
            continue
        top_org = list(go_up_tree(org))[-1]

        row = OrderedDict((
            ('organization title', org.title),
            ('organization name', org.name),
            ('top-level organization title', top_org.title),
            ('top-level organization name', top_org.name),
            ))
        for period_name in all_periods:
            row[period_name] = counts.get(period_name, 0)
        rows.append(row)

    # Group the periods by year, to help the template draw the table nicely
    #all_periods_tuples = [period.split('-') for period in all_periods
    #                      if '-' in period]
    #all_periods_tuples.sort(key=lambda x: x[0])
    #all_periods_by_year = [
    #    (year, [p for y, p in year_periods])
    #    for year, year_periods in groupby(all_periods_tuples, lambda x: x[0])]

    return {'table': rows,
            'all periods': all_periods,
            #'all periods by year': all_periods_by_year
            }

def publisher_report_option_combinations():
    return ({'metric': metric}
            for metric in ('views', 'visits', 'downloads', 'viewsdownloads'))

publisher_report_info = {
    'name': 'site-usage-publisher',
    'title': 'Site usage by publisher',
    'description': 'Usage statistics, by publisher for each month. Data is from Google Analytics.',
    'option_defaults': OrderedDict([('metric', 'views')]),
    'option_combinations': publisher_report_option_combinations,
    'generate': publisher_report,
    'template': 'report/publisher.html',
    }
