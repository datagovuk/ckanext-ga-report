
window.viz.loadGaReports = ->
  d3.json '/scripts/json/ga_reports.json', (data)->
    # Create random graphs of 24 months
    randomPie   = (names) -> 
        ( {name:x, value: Math.round(15+Math.random()*15)} for x in names)
    randomMonth = -> return {
        pie1: randomPie(['Internet Explorer','Firefox','Safari','Google Chrome','Opera'])
        pie2: randomPie(['UK','USA','India'])
    }
    data = 
        months: ( new Month(i%12,2012+Math.floor(i/12)) for i in [2..25] )
        monthlydata: ( randomMonth() for i in [2..25] )
    console.log data
    # --
    pie_options = 
      legend: false
      initialDelay: 200
      startAngle: Math.PI/2
      endAngle: Math.PI*5/2
      width: 390
      height: 200
      radius: 80
      innerRadius: 0
      transitionDelay: 0
      transitionDuration: 150
    graph_pie1 = new viz.PieChart('#graph_pie1',data.monthlydata[0].pie1,colorFunction_browsers(),pie_options)
    pie_options.initialDelay += 150
    graph_pie2 = new viz.PieChart('#graph_pie2',data.monthlydata[0].pie2,d3.scale.category20(),pie_options)

    setMonthData = (monthData) ->
      graph_pie1.setData( monthData.pie1 )
      graph_pie2.setData( monthData.pie2 )

    # Bind the month selector to graphs
    slider = $('<input type="text">').appendTo('#monthselector').slider(
      min:0
      max:data.months.length-1
      step:1
      orientation: 'horizontal'
      value:data.months.length-1
      tooltip: 'show'
      handle: 'round'
      formater: (x) -> data.months[x]
    )
    currentVal = data.months.length-1

    headline_month = new viz.Headline(d3.select('#headline_month'), data.months[currentVal], '')

    updateMonth = (e) ->
        val = e.value
        if val==currentVal then return
        console.log "MonthSelector selects #{data.months[val]} val=#{val} currentVal=#{currentVal}"
        headline_month.update(data.months[val])
        currentVal = val
        setMonthData data.monthlydata[val]

    for item in data.monthlydata[ data.monthlydata.length-1 ].pie1
        icon = icon_for_browser(item.name)
        $("<img src=\"#{icon}\" width=\"24\"/>").appendTo('.piecharts')

    slider.on 'slide',updateMonth
    for x in [0...data.months.length-1]
        percentage = (x*100) / (data.months.length-1)
        tick = $('<div class="slider-tick"/>')
            .appendTo('#monthselector .slider')
            .css('left',"#{percentage}%")
            .toggleClass('major',data.months[x].month==0)
            .toggleClass('first',x==0)
        if data.months[x].month==0 or x==0
            $('<div class="caption"/>').text(data.months[x].year).appendTo(tick)

colorFunction_browsers = ->
    lookup = d3.scale.category20()
    known = 
        'Internet Explorer' : '#05559c'
        'Firefox'           : '#f79f23'
        'Safari'            : '#c7c4c5'
        'Google Chrome'     : '#fdd901'
        'Opera'             : '#e91716'
    return (x) ->
        if x of known then return known[x]
        console.log("Warning: inventing a color for browser=#{x}")
        return lookup(x)

icon_for_browser = (x)->
    known = 
        'Internet Explorer' : 'internet-explorer_48x48.png'
        'Firefox'           : 'firefox_48x48.png'
        'Safari'            : 'safari_48x48.png'
        'Google Chrome'     : 'chrome_48x48.png'
        'Opera'             : 'opera_48x48.png'
    if x of known then return "/images/#{known[x]}"
    console.log("Warning: no icon for browser=${x}")

    
class Month
    constructor: (@month,@year)->
    toString: -> 
        tmp = ['January','February','March','April','May','June','July','August','September','October','November','December']
        return tmp[@month] + ' ' + @year
