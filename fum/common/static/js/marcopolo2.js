function marcopoloField2(el, opt){
  var data = el.data();
  $.extend(data, opt);

  var ctx = {};
  ctx[data.field] = data.parentid;
  var apiUrl = url(data.parent+'-'+data.child, ctx); // API modification URI (POST, DELETE)
  var searchUrl = data.searchurl; // API search URI (GET)
  var searchDetail = data.searchdetail || data.parent+'_detail'; // Web page link
  var tableEl = $('.table', el);
  var searchEl = $('.search', el);

  // Return if not configured
  if (tableEl.length === 0){
    return;
  }

  function showError(data){
    fumErrors.set('marcopolo', data, 'error');
  }

  var delicon = '<i class="icon-remove pull-right"></i>';
  if (searchEl.length === 0){
    delicon = '';
  }

  function updateTable(data){
    console.log("updateTable", apiUrl, data);
    tableEl.html("");
    $(data).each(function(data){
      var sudoIcon = '';
      if (this.sudo){
        sudoIcon = '<i class="icon-wrench pull-right" title="SUDO rights"></i>';
      }

      if (this.username == undefined){
        var item = $('<tr><td class=""><a href="'+url(searchDetail, {slug:this.name})+'" data-id="'+this.name+'">'+this.name+'</a></td><td>'+delicon+sudoIcon+'</td></tr>');
        var d = this.name;
      } else {
        var item = $('<tr><td class=""><a href="'+url(searchDetail, {slug:this.username})+'" class="status-'+this.google_status+'" data-id="'+this.username+'">'+this.first_name+' '+ this.last_name+'</a></td><td>'+delicon+'</td></tr>');
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
      tableEl.append(item);
    });
  }

  // Autoload items via ajax
  $.getJSON(apiUrl, updateTable);

  searchEl.marcoPolo({
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
      tableEl.html('<tr><td><img src="/static/img/loading.gif" alt="Loading"></td></tr>');
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
      });
    }
  });
}
