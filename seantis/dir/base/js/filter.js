(function($) {

    /* Represents a number of <select> elements which form a filter for
     * the seantis.dir.base categories.
     *
     * Instantiate with a jQuery instance holding the concerned selects.
     */
    var Filter = function (elements) {
        var UNSELECTED = '';
        this.categories = elements;

        // Performs a server request for possible values depending on the given
        // terms. Caches the requests if possible (not yet).
        this.query = function(terms, callback) {
            var search_url = $('#directorySearchForm').attr('data-search-url') + '/filter';
            if (!search_url) {
                return;
            }
            $.getJSON(search_url, terms, callback);
        };

        // Updates the page with the result of the selected filter
        this.update = function(eventindex, callback) {

            // If there's no selection, reset the values
            var first = this.first();
            if (!first) {
                this.reset_from_cache();
                return;   
            }

            var terms = this.terms(eventindex);
            var that = this;

            // Query the server for the possible values
            this.query(terms, function(data) {
                $.each(data, function(key, value) {
                    var index = that.index(key);
                    var selected = that.selected(index);

                    // The first selected item always gets the full list
                    if (index === first)
                        that.options(index, that.category_cache(index));
                    
                    // Only the selects after the last clicked one
                    // are filled with values
                    if (index > eventindex)
                        that.options(index, value);

                    // Reset selection after resetting the options
                    if (!selected)
                        that.select(index, UNSELECTED);
                    else
                        that.select(index, selected);
                });

                if (typeof callback !== 'undefined') {
                    callback(eventindex);
                }
            });
        };

        // Reapplies the selections from the last run by doing a round trip
        // to the server and filter the options accordingly. It's not the
        // most stellar design. It grew historically.
        this.initialize = function() {
            var terms = this.terms(4);
            if (!terms) return;

            var that = this;
            terms.replay = true;

            this.query(terms, function(data) {

                var get_options = function(category, index) {
                    var i = index -1;
                    if (i < data.length) 
                        return data[i][category];
                    else if (index >= 1)
                        return get_options(category, index - 1);
                };

                for (var i=2; i <= 4; i++) {
                    var category = 'cat' + i;
                    var options = get_options(category, i-1);
                    
                    that.options(i, options);

                    if (category in terms) {
                        that.select(i, that.closest(options, terms[category]));
                    }
                }
            });
        };

        // Returns the closest value in the list. E.g 'foo (3)'' will yield
        // 'foo (1)' if the latter but not the former is part of the list
        this.closest = function(list, value) {
            var normalize = function(text) {
                return text.substring(0, text.indexOf('('));
            };
            var normal = normalize(value);
            var result = false;
            
            $.each(list, function(index, item) {
                if (normal == normalize(item)) {
                    result = item;
                    return;
                }
            });

            return result;
        };

        // Returns the search terms
        this.terms = function(lastindex, index, terms) {
            lastindex = typeof(lastindex) !== 'undefined' ? lastindex : 4;
            index = typeof(index) !== 'undefined' ? index : this.first();
            terms = typeof(terms) !== 'undefined' ? terms : {};

            if (! this.selected(index))
                return null;

            var name = this.name(index);
            var category = this.category(index);

            terms[name] = category.val();
            
            if (index < lastindex) {
                this.terms(lastindex, index + 1, terms);
            }

            return terms;
        };

        // Returns the jQuery instance of the given category
        this.category = function(ix) {
            ix = ix - 1; // Everywhere else the index is 1 based
            if (ix >= this.categories.length)
                return null;
            
            return $(this.categories[ix]);
        };

        // Returns the select name of the given category
        this.name = function(index) {
            return 'cat' + index;
        };

        // Returns the index of the given category name or 0
        this.index = function(name) {
            var ix = parseInt(name.substring(3), 10);
            if (isNaN(ix)) {
                return 0;
            }
            return ix;
        };

        // Returns true if the given category exists
        this.exists = function(index) {
            return this.category(index) !== null;
        };

        // Returns the selected value or false if nonexistant or not selected
        this.selected = function(index) {
            if (! this.exists(index))
                return false;

            var value = this.category(index).val();
            if (value === UNSELECTED)
                return false;

            return value;
        };

        // Selects the given value of the given category
        this.select = function(index, value) {
            var category = this.category(index);
            if (category !== null)
                this.category(index).val(value);
        };

        // Returns the first selected category
        this.first = function() {
            for (var index = 1; index <= this.categories.length; index++) {
                if (this.selected(index))
                    return index;
            }  
            return 0;
        };

        // Unselects the given category and all categories on its right
        this.unselect = function(index) {
            if (! this.exists(index))
                return;

            this.category(index).val(UNSELECTED);
            this.unselect(index + 1);
        };

        // Sets or gets the options of the given category
        this.options = function(index, values) {
            if (typeof values === 'undefined')
                return this.get_options(index);
            else
                return this.set_options(index, values);
        };

        // Gets the options of the given category
        this.get_options = function(index) {
            options = [];
            this.category(index).find('option').each(function() {
                options.push($(this).val());
            });
            return options;
        };

        // Sets the options of the given category
        this.set_options = function(index, values) {
            var category = this.category(index);
            if (category) {
                category.find('option').remove();

                // If the array does not contain the unselected value, add it
                if ($.inArray(UNSELECTED, values) === -1) {
                    category.append('<option>' + UNSELECTED + '</option>');
                }

                // Add all values from the array to the select
                $.each(values, function(index, value) {
                    category.append('<option>' + value + '</option>');
                });   

                // IE7 you so silly, why you resize on insert?
                if ($.browser.msie && $.browser.version=="7.0") {
                    category.find('option').parent().css('width', '155px');
                }
            }
        };

        // Returns the cache of the given category
        this.category_cache = function(index) {
            return this.category(index).data('cache');
        };

        // Resets all categories from cache
        this.reset_from_cache = function() {
            for (var ix = 1; ix <= this.categories.length; ix++) {
                this.options(ix, this.category_cache(ix));
            }
        };
    };

    $(document).ready(function() {
        var filter = new Filter($('.seantis-directory-category'));

        $(filter.categories).change(function() {
            var index = filter.index($(this).attr('name'));
            if (isNaN(index))
                console.log('Error parsing element');
            else {
                filter.unselect(index + 1);
                filter.update(index);   
            }
        });

        if (filter.categories.length > 0 && seantis.filtered())
            filter.initialize();
    });
})( jQuery );