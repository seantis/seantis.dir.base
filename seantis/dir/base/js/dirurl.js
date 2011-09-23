if (!this.seantis) this.seantis = {};

this.seantis.remove_from = function(text, character) {
    var pos = text.indexOf(character);
    if (pos > -1) {
        return text.substring(0, pos);
    }
    return text;
}

this.seantis.get_filter_url = function() {
    var base = window.location.href;
    base = seantis.remove_from(base, '?');
    base = seantis.remove_from(base, '#');

    var url = base + '/filter';

    return url;
};