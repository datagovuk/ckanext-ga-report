function renderChart(name, element, renderer) {
    el = document.getElementById(element);
    var graph = new Rickshaw.Graph.JSONP({
        element: el,
        renderer: renderer,
        dataURL: '/data/site-usage/chart?name=' + name,
        width: 540,
        height: 240,
        onComplete: function(transport) {
            var graph = transport.graph;
            var detail = new Rickshaw.Graph.HoverDetail({graph: graph});

            var time = new Rickshaw.Fixtures.Time();
            var months = time.unit('month');

            var xAxis = new Rickshaw.Graph.Axis.Time({graph: graph,timeUnit:months});
            xAxis.render();

            var yax = document.getElementById(element + "_yaxis");
            var yAxis = new Rickshaw.Graph.Axis.Y({graph: graph, orientation: 'left', element: yax,
                tickFormat:Rickshaw.Fixtures.Number.formatKMBT});

            graph.render();
        }
    });
}

function barChart(name, element) {
    renderChart(name, element, "bar");
}

function lineChart(name, element) {
    renderChart(name, element, "line");
}

