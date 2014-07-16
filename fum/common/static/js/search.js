$(document).ready(function(){
    
    $('#id_q').marcoPolo({
        url: url('searchall'),
        formatItem: function (data, $item) {
            return '<i class="type-'+data.type+'"></i>&nbsp;'+data.name+'<i><small class="pull-right">['+data.type+']</small></i>';
        },
        onSelect: function (data, $item) {
            window.location = data.url;
        }
    });
});
