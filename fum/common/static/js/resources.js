var add_resource = function(resource, resources_url) {
  // add DOM element
  var node = $('<div href="#" class="resource" data-toggle="manual" data-type="resource" data-original-title="Add a resource"></div>');
  if(isDefined(resource) && resource.id) {
    node.data('pk', resource.id);
  } else {
    node.hide();
  }
  $('.resource-container').append(node);
  // make it editable
  node.editable({
    url: resources_url,
    title: 'Add a Resource <3',
    value: resource,
    validate: function(value) {
      if(value.url == '' || value.name == '') return 'URL and name required';
    },
    params: function(params) {
      return JSON.stringify(params);
    },
    display: function(value) {
        if(!value) {
            $(this).empty();
            return;
        }
        var html = $('<div>', {class: 'resource-entry'}).css('clear', 'both');
        // CONTENT
        var al = $('<a/>').attr({href: value.url}).html(value.name || 'Empty');
        // add EDIT | DELETE buttons
        var del = $('<button/>', {class: 'resource-delete pull-right btn-small btn-danger'}).html('X');
        var edit = $('<button/>', {class: 'resource-edit pull-right btn-small btn-primary'}).html('edit');
        // LA MAGNIFIQUE
        html.append(al);
        html.append(del);
        html.append(edit);
        $(this).html(html);
    }
   });

  node.on('click', '.resource-edit', function(e) {
    e.stopPropagation();
    e.preventDefault();
    node.editable('toggle');
  });

  node.on('click', '.resource-delete', function(e) {
    var pk = node.data().pk;
    $.ajax({
      url: resources_url,
          type: 'DELETE',
          data: JSON.stringify({pk: pk}),
          contentType: 'application/json'
    });
    node.remove();
  });

  if(!isDefined(resource) || !resource.id) {
    setTimeout(function(){
      node.show();
      $('.resource-edit', node).trigger('click');
    }, 100);
  }
};

$(document).ready(function() {
    'use strict';

    // defined in page-specific handlers
    var resdom = $('.resource-container');
    if(!resdom.length>0) {
      return;
    }
    var c = {};
    c[resdom.data('field')] = resdom.data('parentid');
    var apiResourcesUrl = url(resdom.data('parent')+'-resources', c);
    console.log("registering resources", apiResourcesUrl);

    $('.resource-add').on('click', function(e) {
        add_resource({}, apiResourcesUrl);
    });

    var updateResources = function(data) {
      for(var i=0; i<data.length; i++) {
        add_resource(data[i], apiResourcesUrl);
      };
    }

    if($('.resource-container').length != 0){
      $.getJSON(apiResourcesUrl, updateResources);
    }
});
