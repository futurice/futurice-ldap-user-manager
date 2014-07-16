function umlaut(str) {
  return str
  .replace(/â|à|å|ã|ä|á/ig, "a")
  .replace(/ó|ö|ô|ò|õ|Ø/ig, "o")
  .replace(/ç/ig, "c")
  .replace(/é|ê|è|ë/ig, "e")
  .replace(/š/ig, "s")
  .replace(/ß/ig, "ss")
  .replace(/ú|û|ù|ü/ig, "u")
  .replace(/ý|ÿ/ig, "y")
  .replace(/ž/ig, "z");
}

$(document).ready(function(){
  'use strict';

  var primaryGroups = {
  "-1":{pre:"", name:""},
  "2001":{pre:"", name:"Futurice"},
  "2002":{pre:"", name:"External"},
  "2003":{pre:"c", name:"Customers"}
  };
  var MIN_LENGTH = 2;

  function updateFields(){
    var type = primaryGroups[$('#user-type-selector').val()].pre;
    var first = umlaut($('#id_first_name').val());
    var last = umlaut($('#id_last_name').val());

    if($('#id_first_name').val().length>0 && $('#id_last_name').val() && type !== "c") {
      var email = first.toLowerCase()+"."+last.toLowerCase()+"@futurice.com";
      $('#id_email').val(email).trigger('change');
    }

    var username = type+first.slice(0,1)+last.slice(0,3);
    username = username.toLowerCase();

    if (username.length<MIN_LENGTH || username.length>=MIN_LENGTH){
      // username collision
      $.get(url('users-detail', {username:username}),function(){
        username = type+first.slice(0,2)+last.slice(0,3);
        username = username.toLowerCase();
        $.get(url('users-detail', {username:username}),function(){
          username = type+first.slice(0,3)+last.slice(0,2);
          username = username.toLowerCase();
          $.get(url('users-detail', {username:username}),function(){
            username = ""
          });
        });
      }).always(function() {
        $('#id_username').parent().find("p").remove();
        if(username.length >= MIN_LENGTH){
          $('#id_username').val(username).removeClass("fail").addClass("ok");
        } else if(username.length<MIN_LENGTH) {
          $('#id_username').removeClass("ok").addClass("fail").parent().append('<p class="fail">Username too short (less than '+MIN_LENGTH+' characters)</p>');
        } else {
          $('#id_username').removeClass("ok").addClass("fail").parent().append('<p class="fail">Could not generate a free username, try manually.</p>');
        }
      });
    }
  }

  // Update username when name or type changes
  $('#user-type-selector').change(updateFields);
  $('#id_first_name').change(updateFields);
  $('#id_last_name').change(updateFields);
  $('#id_username').change(function(){
    var that = this;
    $.get(url('users-detail', {username:$(this).val()})).success(function(){
      $(that).removeClass("fail").addClass("ok").parent().find("p").remove();
      $(that).addClass("fail").removeClass("ok").parent().append('<p class="fail">Username already in use.</p>');
    }).error(function(){
      $(that).removeClass("fail").addClass("ok").parent().find("p").remove();
    });
  });
  $('#id_email').change(function(){
    var email = encodeURIComponent($(this).val());
    $.get(url('emails-detail', {address:email})).success(function(){
      $('#id_email').removeClass("ok").addClass("fail").parent().append('<p class="fail">Email already in use</p>');
    }).error(function(){
      $.get(url('emailaliases-detail', {address:email})).success(function(data){
        $('#id_email').removeClass("ok").addClass("fail").parent().append('<p class="fail">Email already in use as alias for '+data.parent+'.</p>');
      }).error(function(){
        $('#id_email').parent().find("p").remove();
        $('#id_email').removeClass("fail").addClass("ok");
      });
    });
  });

  var statusDiv = $('#create-status');
  function addError(text){
    statusDiv.append("<p>"+text+"</p>");
    statusDiv.find("p").addClass("alert").addClass("alert-error");
  }

  function clearError(){
    statusDiv.find("p").remove();
  }
  statusDiv.hide();
  $('#create-user-form').ajaxForm({
    type: 'POST',
    url: url('users-list'),
    beforeSubmit: function(arr, $form, options) {
      $('#create-user-form').hide();
      statusDiv.show();
      statusDiv.find('.bar').css('width', '25%');
      clearError();
    },
    success: function(responseText, statusText){
      statusDiv.find('.bar').css('width', '50%');
      var group = primaryGroups[$('#user-type-selector').val()].name;

      if(group.length == 0) {
        statusDiv.find('.bar').css('width', '100%');
        window.location.replace(url('users_detail', {slug: responseText['username']}));
        return
      }

      $.ajax({
        url: url('users-groups', {username:responseText['username']}),
        type: 'POST',
        dataType: 'json',
        data: JSON.stringify({items: [group]}),
        contentType: 'application/json',
        error: function(){
          addError("Could not add groups to user. Please add groups manually.");
          statusDiv.append('<a href="'+url('users_detail', {slug: responseText['username']})+'" class="btn btn-primary">View</a>');
        },
        success: function(data){
          statusDiv.find('.bar').css('width', '100%');
          window.location.replace(url('users_detail', {slug: responseText['username']}));
        }
      });

    },
    error: function(data, textStatus, error){
      statusDiv.find('.bar').css('width', '0');
      for (var key in data.responseJSON){
        addError(key+", "+data.responseJSON[key]);
      }
      $('#create-user-form').show();
    }
  });
});
