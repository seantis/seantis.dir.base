(function($) {

    $(document).ready(function() {
        $(".seantis-directory-filter-box > span").click(function() {
            var open = $(this).siblings('ul').is(":visible");
            $(".seantis-directory-filter-box > ul").hide();
            if (!open) {
                $(this).siblings('ul').show();
            }
        });
    });
})( jQuery );
