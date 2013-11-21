var TreemapGraph = function (selector, data, chartWidth, chartHeight) {

  var xscale = d3.scale.linear().range([0, chartWidth]),
      yscale = d3.scale.linear().range([0, chartHeight]),
      color = d3.scale.category20(),
      headerHeight = 20,
      headerColor = "#555555",
      transitionDuration = 500,
      root,
      node;

  var treemap = d3.layout.treemap()
      .round(false)
      .size([chartWidth, chartHeight])
      .sticky(true)
      .value(function (d) {
          return d.size;
      });

  var chart = d3.select(selector)
      .append("svg:svg")
      .attr("width", chartWidth)
      .attr("height", chartHeight)
      .append("svg:g");

  child_tip = d3.tip()
    .attr('class', 'd3-tip')
    .offset([-10, 0])
    .html(function(d) { return "<p>" + d.name + "</p><p>" + d.amount.toPrecision(3) + " " + d.unit + " (" + d.location + ")</p><p>" + d.categories + "</p>"; });

  parent_tip = d3.tip()
    .attr('class', 'd3-tip')
    .direction('s')
    .html(function(d) { return "<p>" + d.name + "</p><p>Test second line</p>"; });

  chart.call(child_tip);
  chart.call(parent_tip);

  var colorAdjusterScale = d3.scale.log()
      .domain([1, 2]);

  var colorAdjuster = function (label, variance) {
      return d3.rgb(color(label))
          .darker(0.5)
          .brighter(colorAdjusterScale(Math.min(variance + 1, 2)))
          .toString();
  };

  var TreemapGraphFunction = function (data) {
      node = root = data;
      var nodes = treemap.nodes(root);

      var children = nodes.filter(function (d) {
          return !d.children;
      });
      var parents = nodes.filter(function (d) {
          return d.children;
      });

      // create parent cells
      var parentCells = chart.selectAll("g.cell.parent")
          .data(parents, function (d) {
              return "p-" + d.id;
          });

      var parentEnterTransition = parentCells.enter()
          .append("g")
          .attr("class", "cell parent")
          .on("click", function (d) {
              zoom(d);
          });


      parentEnterTransition.append("rect")
          .attr("width", function (d) {
              return Math.max(0.01, d.dx);
          })
          .attr("height", headerHeight)
          .style("fill", headerColor)
          .on('mouseover', parent_tip.show)
          .on('mouseout', parent_tip.hide);

      parentEnterTransition.append('foreignObject')
          .attr("class", "foreignObject")
          .append("xhtml:body")
          .attr("class", "labelbody")
          .append("div")
          .attr("class", "label");

      // update transition
      var parentUpdateTransition = parentCells.transition().duration(transitionDuration);

      parentUpdateTransition.select(".cell")
          .attr("transform", function (d) {
              return "translate(" + d.dx + "," + d.y + ")";
          });

      parentUpdateTransition.select("rect")
          .attr("width", function (d) {
              return Math.max(0.01, d.dx);
          })
          .attr("height", headerHeight)
          .style("fill", headerColor);

      parentUpdateTransition.select(".foreignObject")
          .attr("width", function (d) {
              return Math.max(0.01, d.dx);
          })
          .attr("height", headerHeight)
          .select(".labelbody .label")
          .text(function (d) {
              return d.name;
          });

      // remove transition
      parentCells.exit()
          .remove();

      // create children cells
      var childrenCells = chart.selectAll("g.cell.child")
          .data(children, function (d) {
              return "c-" + d.id;
          });

      // enter transition
      var childEnterTransition = childrenCells.enter()
          .append("g")
          .attr("class", "cell child")
          .on("click", function (d) {
              zoom(node === d.parent ? root : d.parent);
          })
          .on('mouseover', child_tip.show)
          .on('mouseout', child_tip.hide);

      childEnterTransition.append("rect")
          .classed("background", true)
          .style("fill", function (d) {
              return colorAdjuster(d.parent.name, d.variance);
          });

      childEnterTransition.append('foreignObject')
          .attr("class", "foreignObject")
          .attr("width", function (d) {
              return Math.max(0.01, d.dx);
          })
          .attr("height", function (d) {
              return Math.max(0.01, d.dy);
          })
          .append("xhtml:body")
          .attr("class", "labelbody")
          .append("div")
          .attr("class", "label")
          .text(function (d) {
              return d.name;
          });

      childEnterTransition.selectAll(".foreignObject")
          .style("display", "none");

      // update transition
      var childUpdateTransition = childrenCells.transition().duration(transitionDuration);

      childUpdateTransition.select(".cell")
          .attr("transform", function (d) {
              return "translate(" + d.x + "," + d.y + ")";
          });

      childUpdateTransition.select("rect")
          .attr("width", function (d) {
              return Math.max(0.01, d.dx);
          })
          .attr("height", function (d) {
              return d.dy;
          })
          .style("fill", function (d) {
              return colorAdjuster(d.parent.name, d.variance);
          });

      childUpdateTransition.select(".foreignObject")
          .attr("width", function (d) {
              return Math.max(0.01, d.dx);
          })
          .attr("height", function (d) {
              return Math.max(0.01, d.dy);
          })
          .select(".labelbody .label")
          .text(function (d) {
              return d.name;
          });

      // exit transition
      childrenCells.exit()
          .remove();

      d3.select("select").on("change", function () {
          treemap.value(this.value == "size" ? size : count)
              .nodes(root);
          zoom(node);
      });

      zoom(node);
  };

  function size(d) {
      return d.size;
  }

  function count(d) {
      return 1;
  }

  //and another one
  function textHeight(d) {
      var ky = chartHeight / d.dy;
      yscale.domain([d.y, d.y + d.dy]);
      return (ky * d.dy) / headerHeight;
  }

  function idealTextColor(bgColor) {
      var nThreshold = 105,
          components = d3.rgb(bgColor),
          bgDelta = (components.r * 0.299) + (components.g * 0.587) + (components.b * 0.114);
      return ((255 - bgDelta) < nThreshold) ? "#000000" : "#ffffff";
  }

  function zoom(d) {
      treemap.padding([headerHeight / (chartHeight / d.dy), 0, 0, 0])
      .nodes(d);

      // moving the next two lines above treemap layout messes up padding of zoom result
      var kx = chartWidth / d.dx,
          ky = chartHeight / d.dy,
          level = d;

      xscale.domain([d.x, d.x + d.dx]);
      yscale.domain([d.y, d.y + d.dy]);

      if (node != level) {
          chart.selectAll(".cell.child .foreignObject")
          .style("display", "none");
      }

      var zoomTransition = chart.selectAll("g.cell").transition().duration(transitionDuration)
          .attr("transform", function (d) {
              return "translate(" + xscale(d.x) + "," + yscale(d.y) + ")";
          })
          .each("end", function (d, i) {
              if (!i && (level !== self.root)) {
                  chart.selectAll(".cell.child")
                  .filter(function (d) {
                      return d.parent === node; // only get the children for selected group
                  })
                  .select(".foreignObject .labelbody .label")
                  .style("color", function (d) {
                      return idealTextColor(color(d.parent.name));
                  });

                  chart.selectAll(".cell.child")
                  .filter(function (d) {
                      return d.parent === node; // only get the children for selected group
                  })
                  .select(".foreignObject")
                  .style("display", "")
              }
          });

      zoomTransition.select(".foreignObject")
      .attr("width", function (d) {
          return Math.max(0.01, kx * d.dx);
      })
      .attr("height", function (d) {
          return d.children ? headerHeight : Math.max(0.01, ky * d.dy);
      })
      .select(".labelbody .label")
      .text(function (d) {
          return d.name;
      });

      // update the width/height of the rects
      zoomTransition.select("rect")
          .attr("width", function (d) {
              return Math.max(0.01, kx * d.dx);
          })
          .attr("height", function (d) {
              return d.children ? headerHeight : Math.max(0.01, ky * d.dy);
          })
          .style("fill", function (d) {
              return d.children ? headerColor : colorAdjuster(d.parent.name, d.variance);
          });

      node = d;

      if (d3.event) {
          d3.event.stopPropagation();
      }
  }

  TreemapGraphFunction(data);
};
