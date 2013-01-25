var CKAN = CKAN || {};
CKAN.GA_Reports = {};

CKAN.GA_Reports.render_rickshaw = function( css_name, data, mode, colorscheme ) {
    var graphLegends = $('#graph-legend-container');

    if (!Modernizr.svg) {
        $("#chart_"+css_name)
          .html( '<div class="alert">Your browser does not support vector graphics. No graphs can be rendered.</div>')
          .closest('.rickshaw_chart_container').css('height',50);
        var myLegend = $('<div id="legend_'+css_name+'"/>')
          .html('(Graph cannot be rendered)')
          .appendTo(graphLegends);
        return;
    }
    var myLegend = $('<div id="legend_'+css_name+'"/>').appendTo(graphLegends);

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
    var x_axis = new Rickshaw.Graph.Axis.Time( { graph: graph } );
    var y_axis = new Rickshaw.Graph.Axis.Y( {
        graph: graph,
        orientation: 'left',
        tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
        element: document.getElementById('y_axis_'+css_name)
    } );
    var legend = new Rickshaw.Graph.Legend( {
        element: document.querySelector('#legend_'+css_name),
        graph: graph
    } );
    var shelving = new Rickshaw.Graph.Behavior.Series.Toggle( {
      graph: graph,
      legend: legend
    } );
    graph.render();
};

CKAN.GA_Reports.bind_sparklines = function() {
  /* 
   * Bind to the 'totals' tab being on screen, when the 
   * Sparkline graphs should be drawn.
   * Note that they cannot be drawn sooner.
   */
  $('a[href="#totals"]').on(
    'shown', 
    function() {
      var sparkOptions = {
        enableTagOptions: true,
        type: 'line',
        width: 100,
        height: 26,
        chartRangeMin: 0,
        spotColor: '',
        maxSpotColor: '',
        minSpotColor: '',
        highlightSpotColor: '000000',
        lineColor: '3F8E6D',
        fillColor: 'B7E66B'
      };
      $('.sparkline').sparkline('html',sparkOptions);
    }
  );
};

CKAN.GA_Reports.bind_sidebar = function() {
  /* 
   * Bind to changes in the tab behaviour: 
   * Show the correct rickshaw graph in the sidebar. 
   * Not to be called before all graphs load.
   */
  $('a[data-toggle="hashchange"]').on(
    'shown',
    function(e) {
      var href = $(e.target).attr('href');
      var pane = $(href);
      if (!pane.length) { console.err('bad href',href); return; }
      var legend_name = "none";
      var graph = pane.find('.rickshaw_chart');
      if (graph.length) {
        legend_name = graph.attr('id').replace('chart_','');
      }
      legend_name = '#legend_'+legend_name;
      $('#graph-legend-container > *').hide();
      $(legend_name).show();
    }
  );
};

/* 
 * Custom bootstrap plugin for handling data-toggle="hashchange".
 * Behaves like data-toggle="tab" but I respond to the hashchange.
 * Page state is memo-ized in the URL this way. Why doesn't Bootstrap do this?
 */
$(function() {
  var mapping = {};
  $('a[data-toggle="hashchange"]').each(
    function(i,link) {
      link = $(link);
      mapping[link.attr('href')] = link;
    }
  );
  $(window).hashchange(function() {
    var link = mapping[window.location.hash];
    if (link) { link.tab('show'); }
  });
});
