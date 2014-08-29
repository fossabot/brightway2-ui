// From https://github.com/wyuenho/backgrid/issues/62
var ClickableRow = Backgrid.Row.extend({
  events: {
    "click": "onClick"
  },
  onClick: function () {
    Backbone.trigger("rowclicked", this.model);
  }
});


var BackgridTable = function (data, columns, selector, fields, placeholder, nrows, click_callback) {
  var bgModel = Backbone.Model.extend({});
  if (nrows) {
    var bgCollection = Backbone.PageableCollection.extend({
      model: bgModel,
      state: {
        pageSize: nrows
      },
      mode: "client" // page entirely on the client side
    });
  } else {
    var bgCollection = Backbone.Collection.extend({
      model: bgModel,
    });
  }
  var collection = new bgCollection(data);
  var grid = new Backgrid.Grid({
    columns: columns,
    collection: collection,
    row: ClickableRow
  });

  var element = $(selector);
  element.append(grid.render().$el);

  if (fields) {
    var paginator = new Backgrid.Extension.Paginator({
      collection: collection
    });

    element.append(paginator.render().$el);

    var filter = new Backgrid.Extension.ClientSideFilter({
      collection: collection.fullCollection,
      fields: fields, // e.g. ['name']
      placeholder: placeholder, // e.g. "Filter by name"
      wait: 200
    });

    element.prepend(filter.render().$el);

    filter.$el.css({float: "right", margin: "20px"});
  }

  if (click_callback) {
    Backbone.on("rowclicked", click_callback);
  }

  return grid;
};
