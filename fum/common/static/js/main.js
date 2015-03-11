var apiResourcesUrl = '#';

/*
 * X-Editable configurations
 */
$.fn.editable.defaults.mode = 'inline';
$.fn.editable.defaults.send = 'always';
$.fn.editable.defaults.ajaxOptions = {type: "patch", contentType: "application/json"};
$.fn.editable.defaults.error = function(response){
    return response.responseJSON.detail;
};
$.fn.editable.defaults.params = function(params) {
    var r = {};
    r[params.name] = params.value;
    return JSON.stringify(r);
};

$.fn.editable.defaults.select2 = {
    placeholder: "None",
    allowClear: true,
};

(function addXEditable(){
    // Add standard editable to all elements with .xeditable
    $(".xeditable").each(function(){
        if ($(this).is($('#phone1')) || $(this).is($('#phone2'))) {
            // purpose? seems redundant?
            $(this).editable({display: function(value, sourceData) {
                if (sourceData) {
                  $(this).text(sourceData[$(this).attr('id')]);
                }
            }});
        } else if ($(this).data("type") === "select2"){
            // populate xeditable.select2 autocompletion values
            var that = this;
            var url = $(this).data("select");
            $.getJSON(url, function(apidata){
                var results = [];
                for(var i=0; i<apidata.length; i++){
                    results.push({id: apidata[i].name, text: apidata[i].name});
                }

                $(that).editable({source: results});
            });

        } else {
          $(this).editable({display: null});
        }
    });
})();

function validatePassword(password) {
    if (password.length < 10) {
        return "Password has to be at least 10 characters long";
    }

    lower_case = new RegExp('[a-z]').test(password);
    upper_case = new RegExp('[A-Z]').test(password);
    numbers = new RegExp('[0-9]').test(password);
    special = new RegExp('[^a-zA-Z0-9]').test(password);

    if (lower_case + upper_case + numbers + special < 3) {
        return "You must have characters from at least 3 character groups (a-z, A-Z, 0-9, special)";
    }

    return "OK";
}

$(document).ready(function(){
	// Datatables for tables
	var dt = $(".listtable").dataTable({
		"bPaginate": false,
		"bLengthChange": false,
		"bFilter": true,
		"bSort": true,
		"bInfo": false,
		"bAutoWidth": false,
		"sDom": "t"
	    });

	$(".object-search").keyup(function() {
		dt.fnFilter( $(this).val() );
	    });

	/* ##############################################
	 * User's portrait image upload & download begins
	 */
  // in photo.js
  //
	/* User's portrait image upload & download ends
	 * ############################################
	 */

	/* ###############################
	 *  Password changing stuff begins
	 */
	$('#password-modal').on('shown', function() {
		$('#password-modal input:visible').first().focus();
	    });

	$('#password-modal').on('hide', function() {
		$('#password-new, #password-new-again, #password-current').val('');
		$('#password-status, #password-status-again').html('');
		$('#password-new-again').change();
	    });
	/* validations */
	$('#password-new').bind("change paste keyup", function() {
		$('#password-status').html(validatePassword($(this).val()));
		$('#password-new-again').change();
	    });

	$('#password-new-again').bind("change paste keyup", function() {
		var state = "No match";
		if ($(this).val() === $('#password-new').val() && $(this).val().length > 0) {
		    state = "OK";
		    if (validatePassword($('#password-new').val()) === "OK") {
			$('#password-change').removeClass('btn-warning').addClass('btn-success').removeAttr('disabled');
		    }
		} else {
		    $('#password-change').removeClass('btn-success').addClass('btn-warning').attr('disabled', 'disabled');
		}
		if ($(this).val().length < 1) {
		    state = "";
		}
		$('#password-status-again').html(state);
	    });

	/* custom ajax post */
	$('#password-change').click(function() {
		if ($('#password-new').val() === $('#password-new-again').val() && validatePassword($('#password-new').val()) === "OK") {
		    $.post($(this).attr('data-url'), { 'password': $('#password-new').val(), 'old_password': $('#password-current').val() || "" })
			.done(function() { $('#password-cancel').click(); })
			.fail(function(data) { $('#password-status-again').html(data.responseText); });
		} else {
		    return;
		}
	    });
	/* Password changing stuff ends
	 * ############################
	 */


    /* #########################
     * Sudo-button stuff begins
     */
     (function(){
        'use strict';

        $('#confirmPassword').on('shown', function () {
            $("#sudoPassword").focus()
        });

        $('#confirmPasswordForm').submit(function(e){
            e.preventDefault();
            var password = $("#sudoPassword").val();
            $.ajax({

                url: url('enable_superuser'),
                type: 'POST',
                data: {password: password},
                error: function(data){
                    $("#confirmPassError").html(data.responseJSON.desc).addClass("alert").addClass("alert-error");
                },
                success: function(data){
                    window.location.reload();
                },
            });
        });

        $('#endSudo').click(function(e){
            e.preventDefault();
            $.ajax({
                url: url('end_superuser'),
                type: 'POST',
                error: function(data){
                    $("#errorMessage").html(data.responseJSON.desc).addClass("alert").addClass("alert-error");
                },
                success: function(data){
                    window.location.reload();
                },
            });
        });

        var sudoEnds = parseInt($('#sudotime-ends').html());
        var interval = 1; // Interval to update in seconds

        $('#extendSudo').click(function(e){
            e.preventDefault();
	    $.post(url('enable_superuser'), function(data) {
		    sudoEnds = parseInt(data.desc);
                    updateSudoTimer();
		})
		.fail(function(data) {
		    $("#errorMessage").html(data.responseJSON.desc).addClass("alert").addClass("alert-error");
		});
        });

        function updateSudoTimer(){
            var timeLeft = (sudoEnds - Math.floor(new Date().getTime()/1000));
            var error = $('#errorMessage');
            if (timeLeft <= 0) {
                fumErrors.set("sudo", "Your sudo session has expired. Please refresh the page.", "danger");
                $('#sudotimeleft').html("0");
		        clearInterval(sudoTimerId);
            } else if (timeLeft <= 60){
                fumErrors.set("sudo", "Sudo session will expire in less than a minute.", "warning");
                $('#sudotimeleft').html(Math.ceil(timeLeft));
            } else if (timeLeft < 5*60){
                fumErrors.set("sudo","Sudo session will expire in "+Math.ceil(timeLeft/60)+" minutes.", "warning");
                $('#sudotimeleft').html(Math.ceil(timeLeft/60));
            } else {
                $('#sudotimeleft').html(Math.ceil(timeLeft/60));
            }
        };
	if(sudoEnds > 0) {
	    updateSudoTimer();
	    var sudoTimerId = setInterval(updateSudoTimer, interval*1000);
	}
    })();
    /* Sudo-button stuff ends
     * #######################
     */


    /* #######################
     * Aliases-field stuff begins
     */

    (function(){
        'use strict';

        var input = $("#aliases-input");
        var table = $("#aliases-table");
        var url = table.data('url');
        var error = $("#errorMessage");

        function showError(data){
                error.html(data.responseJSON.desc).addClass("alert").addClass("alert-error");
        }

        function updateAliases(data){
            table.html("");
            $(data).each(function(alias){
                var delicon = '<i class="icon-remove pull-right"></i>';
                if ($('#aliases-input').length === 0){
                    // The field is not editable, so don't show the delete icon
                    delicon = '';
                }

                var aliaselement = $('<tr><td class="email-alias"><a href="mailto:'+this+'">'+this+'</a>'+delicon+'</td><td></td></tr>');
                var that = this;
                aliaselement.find('i').click(function(e){
                $.ajax({
                    url: url,
                    type: 'DELETE',
                    data: JSON.stringify({items: [that]}),
                    contentType: 'application/json',
                    error: function(){
                        fumErrors.set('aliasnotset', 'Unable to delete alias.', 'error');
                    },
                    success: updateAliases
                    });
                });
                table.append(aliaselement);
            });
            fumErrors.remove('aliasnotset');
        }

        function addAlias(e){
            e.preventDefault();
            var alias = input.val();
            input.val("");
            if (alias.length > 0){
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: JSON.stringify({items: [alias]}),
                    contentType: 'application/json',
                    error: function(data){
                        fumErrors.set('aliasnotset', 'Unable to add alias: '+data.responseText, 'error');
                        input.addClass('fail');
                    },
                    success: function(data){updateAliases(data);input.removeClass('fail')}
                });
            }
         }
         // Can't use .submit(...) because forms are not allowed in tables.
        $("#add-aliases").click(addAlias);
        input.keypress(function(e) {
            if(e.which == 13) {
                addAlias(e);
            }
        });

        if(table.length>0) {
          $.ajax({
              url: url,
              type: 'GET',
              success: updateAliases
          });
        }

    })();

    /* Aliases stuff ends
     * #####################
     */


     /* Delete group
      * #############
      */
    $("#delete-group-modal .confirm").click(function(){
        $.ajax({
            url: $("#delete-group").data("url"),
            type: "DELETE",
            success: function(data, status){fumErrors.set("deletegroup", "Group deleted.", "success");},
            error: function(data, status){fumErrors.set("deletegroup", "Unable to delete item. " + data.statusText, "danger");},
            complete: function(data, status){$("#delete-group-modal").modal('hide');},
        });
    });
    $("#delete-group").click(function(){
        $("#delete-group-modal").modal('show');
    });

     /*
      * Enable chosen.js when adding groups, projects or servers.
      */
     $(".chosen-select").each(function(){
        $(this).chosen();
     })

    $('.marcopolofield').each(function() {
      marcopoloField2($(this));
    });
});

fumErrors = {
    items: [],
    set: function(id, text, type){
        for (var i=0; i < this.items.length; i++){
            if (this.items[i].id === id){
                this.items[i] = {id:id, text:text, type:type};
                this.update();
                return
            }
        }
        this.items.push({id: id, text: text, type:type});
        this.update();
    },
    remove: function(id){
        for (var i=0; i < this.items.length; i++){
            if (this.items[i].id === id){
                this.items.splice(i, 1);
            }
        }
        this.update();
    },
    update: function(){
        var errors = $("#errorMessage");
        errors.html("");
        $(this.items).each(function(){
            errors.append("<p class='alert alert-"+this.type+"'>"+this.text+"</p>");
        });
        document.body.scrollTop = document.documentElement.scrollTop = 0;
    }
};

function join_this(el) {
  var ctx = {};
  ctx [el.data('field')] = el.data('parentid');
  var apiUrl = url(el.data('parent')+'-'+el.data('child'), ctx);
  $.ajax({
    url: apiUrl,
    type: 'POST',
    data: JSON.stringify({items: [request_user]}),
    contentType: 'application/json',
    error: function(data) {
      fumErrors.set('marcopolo', data, 'error')
    },
    success: function(data){
      window.location.reload();
    }
  });
}

