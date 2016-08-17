function addField(area) {
    var holding_cell = area.getElementsByClassName('multicharfields')[0]
    if (holding_cell.count == undefined) {
        holding_cell.count = holding_cell.childNodes.length + 10
    } else {
        holding_cell.count = holding_cell.count + 1
    }

    var new_column = area.getElementsByClassName('multicharblank')[0].children[0].cloneNode(true);
    console.log(new_column)
    holding_cell.appendChild(new_column);
}

function removeField(field) {
    findFieldGrouper(field).remove()
}

function findFieldGrouper (el) {
    // If the user has altered the structure that holds the field make sure we get the right one
    // The right one being an element that is a child of the span.multicharfields object.
    while ((el = el.parentElement) && !el.parentElement.classList.contains('multicharfields'));
    return el;
}


$(document).ready(function() {

var fieldfinder = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  prefetch: '/data/ac-field/',
  remote: {
    url: '/data/ac-field/?q=%QUERY',
    wildcard: '%QUERY'
  },
  limit: 100,
});

$('.lineup_text').typeahead(null, {
  name: 'ta-',
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
        console.log(data);
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
});

});