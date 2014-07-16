/*
 * Ajax search/add for multiselect fields like user's groups or group's members
 */
function marcopoloField(configs){
    var user = configs['user'];                 // Username
    //var item = configs['item'];                 // The user, group, server or project currently being edited.
    var apiUrl = configs['apiUrl'];             // The API endpoint to POST and DELETE to
    var searchUrl = configs['searchUrl'];       // The url to query for matching users/groups to add
    var tableId = configs['tableId'];           // The ID of the table showing the current users/groups
    var searchId = configs['searchId'];         // ID of the search box

    // Return if not applicable configs
    if ($(tableId).length === 0){
        return;
    }

    function showError(data){
        fumErrors.set('marcopolo', data, 'error');
    }

    var delicon = '<i class="icon-remove pull-right"></i>';
        if ($(searchId).length === 0){
            delicon = '';
        }

    /*
     * Function for updating the table of items
     */
    function updateTable(data){
        console.log("updateTable", apiUrl, data);
        $(tableId).html("");
        $(data).each(function(data){
          var sudoIcon = '';
          if (this.sudo){
            sudoIcon = '<i class="icon-wrench pull-right" title="SUDO rights"></i>';
          }

          if (this.username == undefined){
              var item = $('<tr><td class=""><a href="'+url(configs.reverse.detail, {slug:this.name})+'">'+this.name+'</a></td><td>'+delicon+sudoIcon+'</td></tr>');
              var d = this.name;
          } else {
              var item = $('<tr><td class=""><a href="'+url(configs.reverse.detail, {slug:this.username})+'" class="status-'+this.google_status+'">'+this.first_name+' '+ this.last_name+'</a></td><td>'+delicon+'</td></tr>');
              var d = this.username;
          }

          item.find('i[class*="icon-remove"]').click(function(e){
            $.ajax({
              url: apiUrl,
                  type: 'DELETE',
                  data: JSON.stringify({items: [d]}),
                  contentType: 'application/json',
                  error: showError,
                  success: updateTable
                  });
          })
          $(tableId).append(item);
        });
    }

    /*
     * Request the items via ajax
     */
    $.getJSON(apiUrl, updateTable);


    /*
     * Enable Marco Polo for searching via ajax
     */
    $(searchId).marcoPolo({
	    url: searchUrl,
		formatItem: function (data, $item) {
                if (data.username == undefined){
                    return data.name;
                } else {
                    return data.first_name + " " + data.last_name;
                }
	    },
		onSelect: function (data, $item) {
                this.val("");
                $(tableId).html('<tr><td><img src="/static/img/loading.gif" alt="Loading"></td></tr>');
                if (data.username == undefined){
                    var d = data.name;
                } else {
                    var d = data.username;
                }
                $.ajax({
                    url: apiUrl,
                    type: 'POST',
                    data: JSON.stringify({items: [d]}),
                    contentType: 'application/json',
                    error: showError,
                    success: updateTable,
			    });// end ajax
	    }
	});
}
