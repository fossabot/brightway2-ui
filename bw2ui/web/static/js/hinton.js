var hinton_matrix = function (data, total, xlabels, ylabels, id, w, h, padding) {
  // Transform data for areal display
  t_data = [];
  for (var i = data.length - 1; i >= 0; i--) {
    t_data.push([data[i][0], data[i][1], Math.sqrt(data[i][2])]);
  }
  data = t_data;

  var rows = xlabels.length + 1,
    cols = ylabels.length + 1;
    delta_x = (w - 2 * padding) / cols,
    delta_y = (h - 2 * padding) / rows,
    total = Math.sqrt(total);
    // max_size = d3.max(data, function (d) { return d[2]; });

  if (xlabels.length < d3.max(data, function (d) { return d[0]; }) + 1) {
    throw "Not enough xlabels";
  }

  if (ylabels.length < d3.max(data, function (d) { return d[1]; }) + 1) {
    throw "Not enough ylabels";
  }

  var x_lines = [];
  for (var i = 1; i <= rows; i++) {
    x_lines.push([[1, i], [cols, i]]);
  }

  var y_lines = [];
  for (var i = 1; i <= cols; i++) {
    y_lines.push([[i, 1], [i, rows]]);
  }

  var color_scale = d3.scale.linear()
    .range(["cornflowerblue", "crimson"])
    .domain([0, total]);

  var x_size_scale = d3.scale.linear()
    .range([1, delta_x - 1])
    .domain([0, total]);

  var y_size_scale = d3.scale.linear()
    .range([1, delta_y - 1])
    .domain([0, total]);

  var y = d3.scale.linear()
    .range([padding, h - padding])
    .domain([0, cols]);

  var x = d3.scale.linear()
    .range([padding, w - padding])
    .domain([0, rows]);

  var grid_line = d3.svg.line()
    .x(function(d) { return x(d[0]); })
    .y(function(d) { return y(d[1]); });

  var svg = d3.select(id)
    .append("svg")
    .attr("width", w)
    .attr("height", h);

  var rect = svg.selectAll("rect")
    .data(data)
    .enter().append("rect")
      .attr("x", function (d) { return x(d[0] + 1.5) - (x_size_scale(d[2]) * 0.5); })
      .attr("y", function (d) { return y(d[1] + 1.5) - (y_size_scale(d[2]) * 0.5); })
        // delta_x / 2 + x(d[1]) - x_size_scale(Math.sqrt(d[2]) / 2); })
      // .attr("y", function (d) { return delta_y / 2 + y(d[0]) - y_size_scale(Math.sqrt(d[2])) / 2; })
      .attr("width", function (d) { return x_size_scale(d[2]); })
      .attr("height", function (d) { return y_size_scale(d[2]); })
      .attr("fill", function (d) { return color_scale(d[2]); });

  for (var i = ylabels.length - 1; i >= 0; i--) {
    svg.append("svg:foreignObject")
      .attr('x', x(i + 1) + 1)
      .attr('y', 1)
      .attr("width", delta_x - 2)
      .attr("height", delta_y - 2)
      .append("xhtml:body")
      .html("<div class=\"hinton-label\" title=\"" + ylabels[i] + "\">" + ylabels[i] + "</div>");
  }

  for (var i = xlabels.length - 1; i >= 0; i--) {
    svg.append("svg:foreignObject")
      .attr('x', 1)
      .attr('y', y(i + 1) + 1)
      .attr("width", delta_x - 2)
      .attr("height", delta_y - 2)
      .append("xhtml:body")
      .html("<div class=\"hinton-label\" title=\"" + xlabels[i] + "\">" + xlabels[i] + "</div>");
  }

  svg.selectAll(".x-lines")
    .data(x_lines)
    .enter().append("path")
    .attr("class", "grid-line")
    .attr("d", grid_line);

  svg.selectAll(".y-lines")
    .data(y_lines)
    .enter().append("path")
    .attr("class", "grid-line")
    .attr("d", grid_line);
};