$(document).ready(function() {
  'use strict';

  var user = $("#profile-username").html();

  var defaultTrigger = window.Select2.class.abstract.prototype.triggerChange;
  window.Select2.class.abstract.prototype.triggerChange = function(details) {
    details = details || {};
    details = $.extend({}, details, { klass: this});
    defaultTrigger.apply(this, [details]);
  };

  $('#sudo_change_password').on('click', function(e) {
    var $self = $(this);
    var el = $('<div class="yellow">A moment...</div>');
    $self.after(el);
    e.preventDefault();
    var url = $self.attr('href');
    $self.remove();
    $.post(url, function(data) {
      el.html(data);
    });
  });

  $('.user-status-container').on('change', 'select', function(e) {
    $('#status[class*="status"]').removeClass(function(k, c) {
      var remove_classes = c.match(/status-\w+/g).join(" ");
      return remove_classes;
    });
    $('#status').addClass('status-'+$(this).val());
  });
  $('#status').on('save', function(e, params) {
    window.location = window.location.href;
  });

  $("#xsupervisor").select2({
    placeholder: "Choose:",
    minimumInputLength: 1,
    api_edit_url: url('users-detail', {username: user}),
    api_field: 'supervisor',
    ajax: {
      url: url('users-list'),
      dataType: 'json',
      data: function (term, page) {
        return {
          name: term,
          format: 'json',
          fields: 'id,username,first_name,last_name',
          limit: 0
        };
      },
      results: function(data, page) {
        return {results: data};
      }
    },
    initSelection: function(element, callback) {
      var id = $(element).val();
      var username = $(element).data('initial');
      if (id!=="") {
        $.ajax(url('users-detail', {username: username}), {
          data: {
          },
          dataType: "json"
        }).done(function(data) { callback(data); });
      }
    },
    formatResult: function(r) {
      return r.first_name + ' ' + r.last_name;
    },
    formatSelection: function(r) {
      return r.first_name + ' ' + r.last_name;
    },
    allowClear: true,
    dropdownCssClass: "bigdrop",
    escapeMarkup: function (m) {
      return m;
    }
  }).change(function(e){
    if(e.added || e.removed) {
      var data = {};
      data[e.klass.opts.api_field] = e.val;
      $.ajax({
          url: e.klass.opts.api_edit_url,
          type: 'PATCH',
          data: data,
          error: function(data){
            console.log("error",data);
          },
          success: function(data){
            console.log("success",data);
          },
      });
    }
  });
});

