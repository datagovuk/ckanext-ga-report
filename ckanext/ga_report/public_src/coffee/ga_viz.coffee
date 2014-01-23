window.viz ?= {}

$ ->
  d3.json '/scripts/json/ga_reports.json', (data)->
    #console.log data
    # Create empty graphs
    dummy1 = new viz.Dummy('#dummy1',data.monthlydata[0].pie1,d3.scale.category20())
    graph_pie1 = new viz.PieChart('#graph_pie1',data.monthlydata[0].pie1,d3.scale.category20())
    #graph_pie2 = new viz.PieChart('#graph_pie2',data.monthlydata[0].pie2,d3.scale.category20())
    #graph_pie3 = new viz.PieChart('#graph_pie3',data.monthlydata[0].pie3,d3.scale.category20())
    #graph_pie4 = new viz.PieChart('#graph_pie4',data.monthlydata[0].pie4,d3.scale.category20())

    setMonthData = (monthData) ->
      dummy1.setData( monthData.pie1 )
      graph_pie1.setData( monthData.pie1 )
      #graph_pie2.setData( monthData.pie2 )
      #graph_pie3.setData( monthData.pie3 )
      #graph_pie4.setData( monthData.pie4 )

    # Bind the month selector to graphs
    d3.select('#monthselector')
      .selectAll('button')
      .data(data.monthlydata)
      .enter()
      .append('button')
      .text((d)->d.datename)
      .on('click', setMonthData)

class viz.Dummy
  constructor: (@selector, data) ->
    assert data, "No Data"
    @setData data

  setData: (data) ->
    divz = d3.select(@selector)
      .selectAll('div')
      .data(data)
    divz
      .enter()
      .append('div')
      .style('width',0)
      .style('overflow','hidden')
      .style('white-space','nowrap')
    divz
      .exit()
      .remove()
    divz
      .text((d)->d.name + ' ('+d.value+')')
      .style('background','#fcf')
      .style('margin-top','2px')
      .transition().duration(800).delay(100)
      .style('width',(d)->100+(d.value*3)+'px')
    divz
      .append('span')
      .classed('inner',true)
      .style('background','#0ff')
      .text((d)->d.value)



class viz.PieChart
    constructor: (selector, data, @colorFunction, @startAngle=0, @endAngle=Math.PI*2) ->
        assert data, 'No data received'
        @width = 220
        @height = 200
        @radius = Math.min(@width, @height) / 2
        @container = d3.select(selector)
          .append("svg")
          .attr("width", @width)
          .attr("height", @height)
          .append("g")
          .attr("transform", "translate("+(@width/2)+"," + (@height/2) + ")")
        @setData data

    setData: (data) ->
        initialArc =
            startAngle : @startAngle
            endAngle   : @startAngle
            value      : 0
        # (array)->(array)
        # Enhances an array of values with {startAngle:..,endAngle:..}
        layoutPieChart = d3.layout.pie()
            .sort((a,b) -> a.name.localeCompare(b.name))
            .value((x)->x.value)
            .startAngle(@startAngle)
            .endAngle(@endAngle)
        # Compute startRadius,endRadius -> svg path
        arcGenerator = d3.svg.arc().outerRadius(@radius)
        arcTween = (d) ->
            # Interpolator takes a pair of objects and interpolate their values
            interpolator = d3.interpolate(@_current,d)
            @_current = d
            return (i) -> arcGenerator(interpolator(i))
        # DOM manip
        paths = @container
            .selectAll('path')
            .data(layoutPieChart(data))
        paths.enter()
            .append('path')
            .each (d) -> @_current = initialArc
        paths.exit()
            .remove()
        paths
            .attr('fill',(d,i)=> @colorFunction d.data.name)
            .transition().duration(800).delay(100)
            .attrTween("d", arcTween)
