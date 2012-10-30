import logging
import operator
import ckan.lib.base as base
import ckan.model as model

_log = logging.getLogger(__name__)

def most_popular_datasets(publisher, count=20):
    from ckanext.ga_report.ga_model import GA_Url

    if not publisher:
        _log.error("No valid publisher passed to 'most_popular_datasets'")
        return ""

    datasets = {}
    entries = model.Session.query(GA_Url).\
        filter(GA_Url.department_id==publisher.name).\
        filter(GA_Url.url.like('/dataset/%')).\
        order_by('ga_url.pageviews::int desc')[:count]
    for entry in entries:
        p = model.Package.get(entry.url[len('/dataset/'):])
        if not p in datasets:
            datasets[p] = {'views':0, 'visits': 0}
        datasets[p]['views'] = datasets[p]['views'] + int(entry.pageviews)
        datasets[p]['visits'] = datasets[p]['visits'] + int(entry.visitors)

    results = []
    for k, v in datasets.iteritems():
        results.append((k,v['views'],v['visits']))

    results = sorted(results, key=operator.itemgetter(1), reverse=True)

    ctx = {
        'dataset_count': len(datasets),
        'datasets': results,

        'publisher': publisher
    }

    return base.render_snippet('ga_report/publisher/popular.html', **ctx)
