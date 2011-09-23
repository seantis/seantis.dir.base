//Let's not polute the global namespace
if (!this.seantis) this.seantis = {};

this.seantis.omit_url_parts = function(url, count) {
    var parts = url.split('/');
    var result = "";

    for (var i=parts.length-1; i >= 0; i--) {
        if (count === 0) {
            result = parts[i] + '/' + result;        
        } else {
            count--;   
        }
    }

    return result;
};

this.seantis.filtered = function() {
    var filtered = null;
    try {
        filtered = document.getElementById('seantis-dir-base-filtered');
    } catch (err) {
        // pass
    }

    if (filtered === null || typeof filtered === 'undefined')
        return false;
    else
        return true;
};