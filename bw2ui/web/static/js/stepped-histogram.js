var stepped_histogram = function (data, xlabel, id, w, h, padding) {
  var y_max = d3.max(data.histogram, function (d) { return d[1]; }),
    x_max = d3.max(data.histogram, function (d) { return d[0]; }),
    x_min = d3.min(data.histogram, function (d) { return d[0]; }),
    median = data.statistics.median,
    lower = data.statistics.interval[0],
    upper = data.statistics.interval[1];

  var y = d3.scale.linear()
    .range([h - padding, padding])
    .domain([0, y_max * 1.1])
    .nice();

  var y_axis = d3.svg.axis()
    .scale(y)
    .ticks(4)
    .orient("left");

  var x = d3.scale.linear()
    .range([padding, w - padding])
    .domain([x_min, x_max])
    .nice();

  var x_axis = d3.svg.axis()
    .scale(x)
    .ticks(6)
    .orient("bottom");

  var svg = d3.select(id)
    .append("svg")
    .attr("width",w)
    .attr("height",h);

  var line = d3.svg.line()
    .x(function(d) { return x(d[0]); })
    .y(function(d) { return y(d[1]); })
    .interpolate("linear");

  var histogram_g = svg.append("svg:g")
    .append("svg:path")
    .attr("class", "ihline")
    .attr("d", line(data.histogram));

  var smooth_g = svg.append("svg:g")
    .append("svg:path")
    .attr("class", "isline")
    .attr("d", line(data.smoothed));

  var indicator_line = d3.svg.line()
    .x(function(d) { return x(d[0]); })
    .y(function(d) { return y(d[1]); });

  svg.append("svg:g")
    .append("svg:path")
    .attr("class", "indicator")
    .attr("d", indicator_line([[median, 0], [median, y_max * 1.05]]));

  svg.append("text")
    .attr("class", "label")
    .attr("text-anchor", "middle")
    .attr("x", x(median))
    .attr("y", y(y_max * 1.05) - 5)
    .text("Median");

  svg.append("svg:g")
      .append("svg:path")
      .attr("class", "indicator")
      .attr("d", indicator_line([[lower, 0], [lower, y_max * 0.95]]));

  svg.append("text")
    .attr("class", "label")
    .attr("text-anchor", "middle")
    .attr("x", x(lower))
    .attr("y", y(y_max * 0.95) - 5 )
    .text("95% lower");

  svg.append("svg:g")
      .append("svg:path")
      .attr("class", "indicator")
      .attr("d", indicator_line([[upper, 0], [upper, y_max * 0.95]]));

  svg.append("text")
    .attr("class", "x label")
    .attr("text-anchor", "middle")
    .attr("x", x(upper))
    .attr("y", y(y_max * 0.95) - 5 )
    .text("95% upper");

  svg.append("svg:g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + (h - padding + 2) + ")")
    .call(x_axis);

  svg.append("svg:g")
   .attr("class", "y axis")
   .call(y_axis);

  svg.append("text")
    .attr("class", "y label")
    .attr("text-anchor", "end")
    .attr("transform", "rotate(-90)")
    .attr("y", padding)
    .attr("x", padding)
    .attr("dy", ".5em")
    .text("Count");

  svg.append("text")
    .attr("class", "x label")
    .attr("text-anchor", "end")
    .attr("x", w)
    .attr("y", h - padding - 5)
    .text(xlabel);
}
