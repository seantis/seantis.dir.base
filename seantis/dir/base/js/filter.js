(function($) {

    $(document).ready(function() {
        $(".seantis-directory-filter-box > span").click(function() {
            $(".seantis-directory-filter-box > ul").hide();
            $(this).siblings('ul').show();
        });
    });
})( jQuery );
