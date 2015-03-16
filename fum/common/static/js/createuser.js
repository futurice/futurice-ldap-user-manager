function umlaut(str) {
  return str
  .replace(/â|à|å|ã|ä|á|ă/ig, "a")
  .replace(/ó|ö|ô|ò|õ|Ø/ig, "o")
  .replace(/ç/ig, "c")
  .replace(/é|ê|è|ë/ig, "e")
  .replace(/ï|î|ì|í/ig, "i")
  .replace(/ñ/ig, "n")
  .replace(/š|ș|ş/ig, "s")
  .replace(/ß/ig, "ss")
  .replace(/ț|ţ/ig, "t")
  .replace(/ú|û|ù|ü/ig, "u")
  .replace(/ý|ÿ/ig, "y")
  .replace(/ž/ig, "z");
}

$(document).ready(function(){
  'use strict';

  var primaryGroups = {
  "-1":{pre:"", name:""},
  "2001":{pre:"", name:COMPANY_NAME},
  "2002":{pre:"", name:"External"},
  "2003":{pre:"c", name:"Customers"}
  };
  var MIN_LENGTH = 2;

  /* Uniquely identifies the latest ‘updateFields()’ call.
   * That function schedules asynchronous work (e.g. AJAX callbacks). If a new
   * ‘updateFields()’ runs, the old callbacks must do nothing.
   */
  var updateFieldsToken = new Object();
  function updateFields(){
    var myTok = new Object();
    updateFieldsToken = myTok;

    var type = primaryGroups[$('#user-type-selector').val()].pre;
    var first = umlaut($('#id_first_name').val());
    var last = umlaut($('#id_last_name').val());

    if($('#id_first_name').val().length>0 && $('#id_last_name').val() && type !== "c") {
      var email = first.toLowerCase()+"."+last.toLowerCase()+EMAIL_DOMAIN;
      $('#id_email').val(email).trigger('change');
    }

    // pop() usernames until one is available or none are left
    var usernameOpts = getUsernameOptions().reverse();
    function getUsernameOptions() {
        var len = 4, left, right, opts = [], uname;
        for (left = 1; left < len; left++) {
            right = len - left;
            uname = (type + first.slice(0, left) +
                    last.slice(0, right)).toLowerCase();
            if (uname.length < MIN_LENGTH) {
                continue;
            }
            opts.push(uname);
        }
        return opts;
    }

    var selector = '#id_username';
    tryNextUsername();
    function tryNextUsername() {
        if (myTok != updateFieldsToken) {
            return;
        }
        if (!usernameOpts.length) {
            $(selector).parent().find("p").remove();
            $(selector).val('').removeClass("ok").addClass("fail").parent().append('<p class="fail">Could not generate a free username, try manually.</p>');
            return;
        }

        var username = usernameOpts.pop();
        $.ajax({
            url: url('users-detail', {username: username}),
            success: tryNextUsername,
            error: function() {
                if (myTok != updateFieldsToken) {
                    return;
                }
                $(selector).parent().find("p").remove();
                $(selector).val(username).removeClass("fail").addClass("ok");
            }
        });
    }
  }

  // Update username when name or type changes
  $('#user-type-selector').change(updateFields);
  $('#id_first_name').change(updateFields);
  $('#id_last_name').change(updateFields);
  $('#id_username').change(function(){
    if ($(this).val().length < MIN_LENGTH) {
      $(this).parent().find("p").remove();
      $(this).removeClass("ok").addClass("fail").parent().append('<p class="fail">Username too short (less than '+MIN_LENGTH+' characters)</p>');
      return;
    }

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
