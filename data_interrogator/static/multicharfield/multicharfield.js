function addColumn(area) {
    var holding_cell = area.getElementsByTagName('span')[0]
    if (holding_cell.count == undefined) {
        holding_cell.count = holding_cell.childNodes.length + 10
    } else {
        holding_cell.count = holding_cell.count + 1
    }

    var new_column = area.getElementsByTagName('span')[1].childNodes[0].cloneNode(true);
    holding_cell.appendChild(new_column);
}

function removeColumn(column) {
    column.parentElement.remove()
}

