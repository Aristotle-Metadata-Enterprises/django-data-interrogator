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


