$.extend($.imgAreaSelect.prototype, {
    animateSelection: function (x1, y1, x2, y2, duration) {
        var fx = $.extend($('<div/>')[0], {
            ias: this,
            start: this.getSelection(),
            end: { x1: x1, y1: y1, x2: x2, y2: y2 }
        });

        $(fx).animate({
            cur: 1
        },
        {
            duration: duration,
            step: function (now, fx) {
                var start = fx.elem.start, end = fx.elem.end,
                    curX1 = Math.round(start.x1 + (end.x1 - start.x1) * now),
                    curY1 = Math.round(start.y1 + (end.y1 - start.y1) * now),
                    curX2 = Math.round(start.x2 + (end.x2 - start.x2) * now),
                    curY2 = Math.round(start.y2 + (end.y2 - start.y2) * now);
                fx.elem.ias.setSelection(curX1, curY1, curX2, curY2);
                fx.elem.ias.update();
            }
        });
    }
});

$(document).ready(function(){

$("#portrait-upload").click(function () {
  $("#portrait-upload-file").click();
});

$("#portrait-upload-file").change(function (event) {
  var file = event.target.files[0];

  if (!file.type.match('image.*')) {
    return;
  }

  var reader = new FileReader();

  reader.onload = (function (f) {
    return function (e) {
      window.portrait = e.target.result;
      var imgOrig = new Image();
      imgOrig.onload = function () {
        $("#portrait-dimensions").html("(" + this.width + "x" + this.height + ")");
        window.portraitImage = this;
      };
      imgOrig.src = e.target.result;
      $("#portrait-preview-crop").attr('src', e.target.result);
      var ias = $("img#portrait-preview-crop").imgAreaSelect({
        aspectRatio: '2:3',
        handles: true,
        instance: true,
        onSelectChange: function (img, selection) {
          var scale = imgOrig.width / img.width;
          $("#portrait-crop-info").html("(" + Math.floor(scale * selection.width) + "x" + Math.floor(scale * selection.height) + ")");
        }
      });
      $("#portrait-modal").modal('show');

      $('#portrait-modal').on('shown.bs.modal', function (e) {
        if(!ias.getSelection().width) {
          ias.setOptions({show: true,
            x1: 0,
            y1: 0,
            x2: 75,
            y2: 100});
        }
        ias.animateSelection(0, 0, 225, 300, 'fast');
      });

    };
  })(file);

  reader.readAsDataURL(file);
});

$("#portrait-modal").on('hide', function () {
  // Clear the file input
  delete window.portrait;
  $("img#portrait-preview-crop").imgAreaSelect({
    remove: true
  });
  $("#portrait-upload-file").val('');
  $("#portrait-crop-info").html('');
});

/* custom ajax post */
$('#portrait-save').click(function () {
  var crop = $("img#portrait-preview-crop").imgAreaSelect({
    instance: true
  }).getSelection();
  var scale = window.portraitImage.width / $("img#portrait-preview-crop").width();
  $.ajax({
    url: $(this).attr('data-url'),
    data: {
      portrait: window.portrait,
      left: Math.round(crop.x1 * scale),
      top: Math.round(crop.y1 * scale),
      right: Math.round(crop.x2 * scale),
      bottom: Math.round(crop.y2 * scale)
    },
    type: 'POST',
    error: function (data) {
      // TODO: log to sentry
      alert("Portrait upload failed: " + data.responseText);
    },
    success: function (data) {
      var j = JSON.parse(data)
      $("#portrait").attr('src', j.thumb);
      $("#portrait-download").attr('href', j.full).attr('style', '');
      $("#portrait-upload-time").html(j.day).attr('title', j.time);
      $("#portrait-cancel").click();
    }
  });
});

});//document.ready
