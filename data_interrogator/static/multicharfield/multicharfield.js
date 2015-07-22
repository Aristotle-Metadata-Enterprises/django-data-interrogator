function addColumn(area) {
    var holding_cell = area.getElementsByTagName('span')[0]
    if (holding_cell.count == undefined) {
        holding_cell.count = holding_cell.childNodes.length + 10
    } else {
        holding_cell.count = holding_cell.count + 1
    }
    console.log(holding_cell.count)

    var new_column = area.getElementsByTagName('span')[1].innerHTML;
    //new_column = new_column.replace('XXX',holding_cell.count)
    holding_cell.innerHTML = holding_cell.innerHTML + new_column;
}
