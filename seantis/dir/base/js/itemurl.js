if (!this.seantis) this.seantis = {};

this.seantis.get_filter_url = function() {
    var base = window.location.href;
    var url = seantis.omit_url_parts(base, 1) + 'filter';
    console.log(url);
    return url;
};