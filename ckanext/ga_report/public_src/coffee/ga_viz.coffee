window.viz ?= {}

$ ->
  d3.json '/scripts/json/ga_reports.json', (data)->
    #console.log data
    # Create empty graphs
    graph_pie1 = new viz.PieChart('#graph_pie1',data.monthlydata[0].pie1,d3.scale.category20(),initialDelay=200)
    graph_pie2 = new viz.PieChart('#graph_pie2',data.monthlydata[0].pie2,d3.scale.category20(),initialDelay=350,startAngle=Math.PI/2,endAngle=Math.PI*5/2)
    graph_pie3 = new viz.PieChart('#graph_pie3',data.monthlydata[0].pie3,d3.scale.category20(),initialDelay=500,startAngle=Math.PI,endAngle=Math.PI*3)
    graph_pie4 = new viz.PieChart('#graph_pie4',data.monthlydata[0].pie4,d3.scale.category20(),initialDelay=650,startAngle=Math.PI*3/2,endAngle=Math.PI*7/2)

    setMonthData = (monthData) ->
      graph_pie1.setData( monthData.pie1 )
      graph_pie2.setData( monthData.pie2 )
      graph_pie3.setData( monthData.pie3 )
      graph_pie4.setData( monthData.pie4 )

    # Bind the month selector to graphs
    d3.select('#monthselector')
      .selectAll('button')
      .data(data.monthlydata)
      .enter()
      .append('button')
      .text((d)->d.datename)
      .on('click', setMonthData)

class viz.PieChart
    constructor: (selector, data, @colorFunction, initialDelay=0, @startAngle=0, @endAngle=Math.PI*2) ->
        assert data, 'No data received'
        width = 220
        height = 200
        @radius = Math.min(width, height) / 2
        @container = d3.select(selector)
          .append("svg")
          .attr("width", width)
          .attr("height", height)
          .append("g")
          .attr("transform", "translate("+(width/2)+"," + (height/2) + ")")
        @transitionDelay = initialDelay
        @transitionDuration = 500
        # Handle entry, update
        @setData data

    ##
    ## This implementation handles beautiful animation but requires
    ## you hand over the same size array in the same order each time.
    ##
    setData: (data) =>
        defaultData = {startAngle:@startAngle,endAngle:@startAngle,value:0}
        # (array)->(array)
        # Enhances an array of values with {startAngle:..,endAngle:..}
        layoutPieChart = d3.layout.pie()
            .sort((a,b) -> a.name.localeCompare(b.name))
            .value((x)->x.value)
            .startAngle(@startAngle)
            .endAngle(@endAngle)
        data = layoutPieChart(data)
        # Compute startRadius,endRadius -> svg path
        arcGenerator = d3.svg.arc().outerRadius(@radius).innerRadius(0)
        centroidArcGenerator = d3.svg.arc().outerRadius(@radius*1.6).innerRadius(0)
        # Entering selection
        # ------------------
        paths = @container.selectAll('path').data(data)
        texts = @container.selectAll('text').data(data)
        paths.enter().append('path')
              .attr('fill',(d,i)=> @colorFunction d.data.name)
        texts.enter().append('text')
              .attr('dy','0.5em')
              .attr('text-anchor','middle')
              .attr('fill-opacity',0)
        # Interpolator takes a pair of objects and interpolate their values
        arcTween = (d) -> 
          interpolator = d3.interpolate(@_current || defaultData,d)
          @_current = d
          return (i) -> arcGenerator(interpolator(i))
        centroidTween = (d) -> 
          interpolator = d3.interpolate(@_current || defaultData,d)
          @_current = d
          return (i) -> 'translate('+centroidArcGenerator.centroid(interpolator(i))+')'
        textTween = (d) -> 
          from = @_current2 || defaultData
          @_current2 = d
          interpolator = d3.interpolate(from,@_current2)
          return (i) ->
            @textContent = ''+Math.round(interpolator(i).value)
        # Update selections
        paths
            .transition().duration(@transitionDuration).delay(@transitionDelay)
            .attrTween("d", arcTween)
        texts.transition().duration(@transitionDuration).delay(@transitionDelay)
            .attrTween("transform", centroidTween)
            .attr('fill-opacity', (d)-> if d.value then 1 else 0 )
            .tween('text',textTween)
        @transitionDuration = 800
        @transitionDelay = 100



# class viz.Dummy
#   constructor: (@selector, data) ->
#     assert data, "No Data"
#     @setData data
# 
#   setData: (data) ->
#     divz = d3.select(@selector)
#       .selectAll('div')
#       .data(data)
#     divz
#       .enter()
#       .append('div')
#       .style('width',0)
#       .style('overflow','hidden')
#       .style('white-space','nowrap')
#     divz
#       .exit()
#       .remove()
#     divz
#       .text((d)->d.name + ' ('+d.value+')')
#       .style('background','#fcf')
#       .style('margin-top','2px')
#       .transition().duration(800).delay(100)
#       .style('width',(d)->100+(d.value*3)+'px')
#     divz
#       .append('span')
#       .classed('inner',true)
#       .style('background','#0ff')
#       .text((d)->d.value)



