(function ($) {
    "use strict";

    var Resource = function (options) {
        this.init('resource', options, Resource.defaults);
    };

    //inherit from Abstract input
    $.fn.editableutils.inherit(Resource, $.fn.editabletypes.abstractinput);

    $.extend(Resource.prototype, {
        /**
        Renders input from tpl

        @method render()
        **/
        render: function() {
           this.$input = this.$tpl.find('input');
        },

        /**
        Gets value from element's html

        @method html2value(html)
        **/
        html2value: function(html) {
          return html;
        },

       /**
        Converts value to string.
        It is used in internal comparing (not for sending to server).

        @method value2str(value)
       **/
       value2str: function(value) {
           var str = '';
           if(value) {
               for(var k in value) {
                   str = str + k + ':' + value[k] + ';';
               }
           }
           return str;
       },

       /*
        Converts string to value. Used for reading value from 'data-value' attribute.

        @method str2value(str)
       */
       str2value: function(str) {
           return str;
       },

       /**
        Sets value of input.

        @method value2input(value)
        @param {mixed} value
       **/
       value2input: function(value) {
           if(!value) {
             return;
           }
           this.$input.filter('[name="name"]').val(value.name);
           this.$input.filter('[name="url"]').val(value.url);
       },

       /**
        Returns value of input.

        @method input2value()
       **/
       input2value: function() {
           return {
              name: this.$input.filter('[name="name"]').val(),
              url: this.$input.filter('[name="url"]').val(),
           };
       },

        /**
        Activates input: sets focus on the first field.

        @method activate()
       **/
       activate: function() {
            this.$input.filter('[name="name"]').focus();
       },

       /**
        Attaches handler to submit form in case of 'showbuttons=false' mode

        @method autosubmit()
       **/
       autosubmit: function() {
           this.$input.keydown(function (e) {
                if (e.which === 13) {
                    $(this).closest('form').submit();
                }
           });
       }
    });

    Resource.defaults = $.extend({}, $.fn.editabletypes.abstractinput.defaults, {
        tpl: '<div class="editable-resource"><label><span>Name: </span><input type="text" name="name" class="input-large"></label></div>'+
             '<div class="editable-resource"><label><span>URL: </span><input type="text" name="url" class="input-large"></label></div>',
        inputclass: ''
    });

    $.fn.editabletypes.resource = Resource;

}(window.jQuery));
