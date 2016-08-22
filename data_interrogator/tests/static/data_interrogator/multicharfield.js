function addField(area) {
    var holding_cell = area.getElementsByClassName('multicharfields')[0]
    if (holding_cell.count == undefined) {
        holding_cell.count = holding_cell.childNodes.length + 10
    } else {
        holding_cell.count = holding_cell.count + 1
    }

    var new_column = area.getElementsByClassName('multicharblank')[0].children[0].cloneNode(true);
    holding_cell.appendChild(new_column);
    $(new_column).find('.lineup_text').typeahead(null, typeahead_settings);
}

function removeField(field) {
    findFieldGrouper(field).remove()
}

function findFieldGrouper (el) {
    // If the user has altered the structure that holds the field make sure we get the right one
    // The right one being an element that is a child of the span.multicharfields object.
    while ((el = el.parentElement) && !el.parentElement.classList.contains('multicharfields'));
    console.log(el);
    return el;
}

function get_model () {
  return document.getElementById("id_lead_suspect").value;
}

var typeahead_settings = {};

function typeahead_init() {
  
  var fieldfinder = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    
    remote: {
      url: '/data/ac-field/?q=%QUERY&model=',
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

  $('.multicharfields .lineup_text').typeahead(null, typeahead_settings);

}