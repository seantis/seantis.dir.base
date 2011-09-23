(function($) {
    var newline = '\n';

    var get_queryurl = function(categoryid) {
        var base = window.location.href;
        if (is_add_url(base)) {
            base = seantis.omit_url_parts(base, 1);
        } else {
            base = seantis.omit_url_parts(base, 2);
        }
        return base + 'query?cat=' + categoryid;
    };

    var is_add_url = function(url) {
        var result = url.indexOf('++add++') > 0;
        return result;
    };

    var get_category = function(categoryid) {
        return $('#form-widgets-cat' + categoryid);
    };

    var get_existing = function(category) {
        var values = category.val().split(newline);
        var existing = [];
        $.each(values, function(index, value) {
            if (value.length >= 1) {
                var item = {};
                item.id = value;
                item.name = value;
            
                existing.push(item); 
            }
        });

        return existing;
    };

    var formatter = function(tokens) {
        var result = "";

        $.each(tokens, function(index, value) {
            result += value.name;
            result += newline;
        });

        return result;
    };

    /* It is not possible to confine this script to seantis.dir.base.item types
    as the resource registry offers way to examine if the item is being added
    or not (in which case the context is seantis.dir.base even though an item
    add form is shown).

    Therefore a guess is made from the class names present in the current html,
    though that might fail sometime in the future.

    See Products.ResourceRegistry.tools.BaseRegistry.evaluateExpression
    */
    var enable = function() {
        var body = $('body').attr('class');

        // template-seantis.dir.....item (add edit view)
        if (/template-seantis\.dir(\..*)?\.item/.test(body))
            return true;

        // apart from that, only template edit views
        if (/template-edit/.test(body) === false)
            return false;
        
        // with the correct portaltype
        if (/portaltype-seantis-dir(-.*)?-item/.test(body))
            return true;
        
        return false;
    };

    var setup_category = function(categoryid) {
        var category = get_category(categoryid);  
        if (category.length <= 0)
            return;

        var queryurl = get_queryurl(categoryid);
        var existing = get_existing(category);
        var delimiter = newline;

        existing = existing.length > 0 ? existing : null;

        category.hide();
        category.tokenInput(
            queryurl,
            {
                tokenDelimiter: delimiter,
                prePopulate: existing,
                tokenValue: 'name',
                preventDuplicates: true,
                allowCustomEntry: true,
                tokensFormatter: formatter,
                hintText: "",
                noResultsText: "",
                searchingText: "...",
                deleteText: "&times;"
            }
        );
    };

    $(document).ready(function() {
        if (enable()) {
            setup_category(1);
            setup_category(2);
            setup_category(3);
            setup_category(4);   
        }
    });
})( jQuery );