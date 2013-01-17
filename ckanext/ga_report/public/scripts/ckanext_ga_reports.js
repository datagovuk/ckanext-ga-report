
var CKAN = CKAN || {};
CKAN.GA_Reports = {};

CKAN.GA_Reports.render_rickshaw = function( css_name, data, mode, colorscheme ) {
    var palette = new Rickshaw.Color.Palette( { scheme: colorscheme } );
    $.each(data, function(i, object) {
        object['color'] = palette.color();
    });

    var graphElement =  document.querySelector("#chart_"+css_name);

    var graph = new Rickshaw.Graph( {
        element: document.querySelector("#chart_"+css_name),
        renderer: mode,
        series: data ,
        height: 328
    });
    graph.render();
    var x_axis = new Rickshaw.Graph.Axis.Time( { graph: graph } );
    var y_axis = new Rickshaw.Graph.Axis.Y( {
        graph: graph,
        orientation: 'left',
        tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
        element: document.getElementById('y_axis_'+css_name),
    } );
    var legend = new Rickshaw.Graph.Legend( {
        element: document.querySelector('#legend_'+css_name),
        graph: graph
    } );
    var hoverDetail = new Rickshaw.Graph.HoverDetail( {
      graph: graph,
      formatter: function(series, x, y) {
        var date = '<span class="date">' + new Date(x * 1000).toUTCString() + '</span>';
        var swatch = '<span class="detail_swatch" style="background-color: ' + series.color + '"></span>';
        var content = swatch + series.name + ": " + parseInt(y) + '<br>' + date;
        return content;
      }
    } );
};

