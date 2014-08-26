var DynamicHypertreeSupplyChain = function (json_data, selector) {
    var infovis = document.getElementById(selector);
    // var w = infovis.offsetWidth - 50, h = infovis.offsetHeight - 50;
    var w = infovis.offsetWidth, h = 600;

    //init Hypertree
    var ht = new $jit.Hypertree({
      //id of the visualization container
      injectInto: selector,
      //canvas width and height
      width: w,
      height: h,
      duration: 250,
      //Change node and edge styles such as
      //color, width and dimensions.
      Node: {
          dim: 10,
          color: "#ffe05c"
      },
      Edge: {
          lineWidth: 4,
          color: "#8368ee"
      },
      Navigation: {
          enable: true,
          panning: true,
          zoom: 20
      },

      //Attach event handlers and add text to the
      //labels. This method is only triggered on label
      //creation
      onCreateLabel: function(domElement, node){
          // domElement.innerHTML = node.name;
          var namely;
          if (node.name.length > 50) {
            namely = node.name.substr(0, 47) + "...";
          } else {
            namely = node.name;
          }

          if (node.data.origin === true) {
            domElement.innerHTML = ('<table cellpadding="1" cellspacing="0" class="scNodeTable">' +
                '<tr><td>' + namely + '</td></tr>' +
                '</table>');
            } else {
                domElement.innerHTML = ('<table cellpadding="1" cellspacing="0" class="scNodeTable">' +
                    '<tr><td colspan=3>' + namely + '</td></tr>' +
                    '<tr><td><a class="scOpen">subchain</a></td>' +
                    '<td><a href="' + node.data.url + '">open</a></td>' +
                    '<td><a class="scClose">close</a></td></tr>' +
                    '</table>');
            }
          $jit.util.addEvent(domElement, 'click', function (event) {
              if (event.target.className == "scClose") {
                var subnodes = node.getSubnodes(0);
                var map = [];
                for (var i = 0; i < subnodes.length; i++) {
                    map.push(subnodes[i].id);
                }
                ht.op.removeNode(map.reverse(), {
                    type: 'fade:seq',
                    duration: 250,
                    hideLabels: false
                });
              } else if (event.target.className == "scOpen") {
                $.ajax({
                    url: node.data.url + "/sc_graph"
                }).done( function (newGraph) {
                    ht.op.sum(newGraph, {
                        type: 'fade:seq',
                        duration: 250,
                        hideLabels: false,
                    });
                });
              } else {
                  ht.onClick(node.id, {
                      onComplete: function() {
                          ht.controller.onComplete();
                      }
                  });
              }
          });

          $jit.util.addEvent(domElement, 'mouseenter', function (event) {
              console.log($(domElement).zIndex());
              $(domElement).zIndex(1);
              $(domElement).children("table").fadeTo(100, 0.95);
          });

          $jit.util.addEvent(domElement, 'mouseleave', function (event) {
              $(domElement).zIndex(0);
              $(domElement).children("table").fadeTo(100, 0.75);
          });
      },

      //Change node styles when labels are placed
      //or moved.
      onPlaceLabel: function(domElement, node){
          var style = domElement.style;
          style.display = '';
          style.cursor = 'pointer';
          if (node._depth <= 1) {
              style.fontSize = "0.8em";
              // style.color = "#ddd";

          } else if(node._depth == 2){
              style.fontSize = "0.7em";
              // style.color = "#555";

          } else {
              style.display = 'none';
          }

          var left = parseInt(style.left);
          var w = domElement.offsetWidth;
          style.left = (left - w / 2) + 'px';
      },
    });

    ht.loadJSON(json_data);
    ht.refresh();
    ht.controller.onComplete();
}
