var typeahead_settings = {};

function new_field(value="") {
    return `
    <div>
    <input type="text" class="typeahead_field" value="${value}" />
    <input type='button' value='-' title='Remove' onclick='removeField($(this))' />
    </div>
    `;
}

function new_section(name, add_text) {
    x = `<div id='id_${name}' data-name="${name}">
    <div class="fields"></div>
    <input type='button' value='${add_text}' onclick='addField($(this.parentElement))' />
    <input type="hidden" value="" name="${name}" id="id_hidden_${name}" />
    </div>`;
    return x;
}

function multichar_init() {
    typeahead_init();
    for (section of ['filter_by', 'columns', 'sort_by']) {
        values = $('#id_'+section).val()
        $('#id_'+section).replaceWith(new_section(section, 'Add new '+section));
        for (val of values.split('||')) {
          addField($('#id_'+section), val)
        }
    }

    $('form').submit(function() {
        for (section of ['filter_by', 'columns', 'sort_by']) {
            var data=[];
            $("#id_"+section+" input.typeahead_field.tt-input").each(function() {
                data.push($(this).val());
            });
            console.log(data)
            $("#id_hidden_"+section).val(data.join("||"));
        }
        return true;
    });

}
function addField(area, value="") {
    var holding_cell = area.find('.fields')[0]
    var new_column = $(new_field(value));
    new_column.find('input.typeahead_field').typeahead(null, typeahead_settings);
    new_column.appendTo(holding_cell);
}

function removeField(field) {
    field.parent().remove()
    return false;
}

function get_model () {
  return document.getElementById("id_lead_base_model").value;
}

function typeahead_init() {
  
  var fieldfinder = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    
    remote: {
      url: './ac?q=%QUERY&model=',
      replace: function (url, query) {
          return url.replace('%QUERY',query)+encodeURIComponent(get_model())
      },
      wildcard: '%QUERY'
    },
    limit: 100,
  });

  typeahead_settings = {
    name: 'ta-data-interrogator',
    source: fieldfinder,
    display: 'value',
    templates: {
      empty: [
        '<div class="empty-message">',
          'unable to find any matching fields',
        '</div>'
      ].join('\n'),
    limit: 100 ,
    suggestion: function (data) {
          lookup = data.lookup
          var name = data.name.replace(new RegExp(lookup, 'g'),'<u>'+lookup+'</u>')
          txt = '<p><strong>' + name + '</strong>';
          if (data.is_relation) {
              txt = txt + "...";
          }
          txt = txt + ' - <small>'+data.datatype+'</small>';
          txt = txt + '<br>' + data.help + '</p>';
          return txt
      }
    }
  }
}