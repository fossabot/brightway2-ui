var interpolated_histogram = function (data, xlabel, median, upper, lower, id, w, h, padding) {
  var y_max = d3.max(data, function (d) { return d[0]; }),
    x_max = d3.max(data, function (d) { return d[1]; }),
    x_min = d3.min(data, function (d) { return d[1]; });

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
    .x(function(d) { return x(d[1]); })
    .y(function(d) { return y(d[0]); })
    .interpolate("linear");

  var g = svg.append("svg:g")
    .append("svg:path")
    .attr("class", "ihline")
    .attr("d", line(data));

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