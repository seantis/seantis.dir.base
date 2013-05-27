if (!seantis) seantis = {};

seantis.maplayer = function(id, url, title, letter, zoom) {
    var kmlurl = url + '@@kml-document?letter=' + letter;

    var layer = new OpenLayers.Layer.Vector(title, {
        protocol: new OpenLayers.Protocol.HTTP({
            url: kmlurl,
            format: new OpenLayers.Format.KML({
                extractStyles: true,
                extractAttributes: true
            })
        }),
        strategies: [new OpenLayers.Strategy.Fixed()],
        projection: cgmap.createDefaultOptions().displayProjection
    });

    var zoom_to = function(layer) {
        layer.map.zoomToExtent(layer.getDataExtent());
        if(layer.features.length>1){
            layer.map.zoomTo(layer.map.getZoom()-1);
        } else {
            layer.map.zoomTo(layer.map.getZoom()-4);
        }
    };

    var link_layer = function(layer, url) {
        // this won't work on ie < 8
        var placemark = $(document.getElementById(layer.id+'_root'));

        if (placemark) {
            placemark.css('cursor', 'pointer');
            placemark.click(function() {
                window.location = url;
                return false;
            });
        }
    };

    var pulsate = function(layer, start) {
        var parent = document.getElementById(layer.id+'_vroot');
        if (!parent) return;

        if (typeof parent.stop_animation !== 'undefined') {
            parent.stop_animation();
            delete parent.stop_animation;
        }

        if (! start) return;

        var elements = parent.childNodes;
        var stops = [];
        for(var i=0; i<elements.length; i++) {
            stops[i] = pulseate_element(elements[i]);
        }
        parent.stop_animation = function() {
            for (var i=0; i<stops.length; i++) {
                stops[i]();
            }
        };
    };

    var get_attr = function(el, attr) {
        return parseInt(el.getAttribute(attr), 10);
    };

    var set_attr = function(el, attr, val) {
        if (isNaN(val)) return;
        el.setAttribute(attr, val);
    };

    var force_topmost = function(layer) {
        var parent = document.getElementById(layer.id+'_vroot');
        if (!parent) return;

        /* append the container holding the marker to the container holding
        all the markers, forcing it to show on top of the other markers (
        essentially what you would usually do with a z-index).

        SVG's render orders is defined solely through element order, which
        is why this is done like that, see:

        http://stackoverflow.com/questions/482115/
        with-javascript-can-i-change-the-z-index-layer-of-an-svg-g-element
        */
        parent.parentNode.parentNode.appendChild(parent.parentNode);
    };

    var pulseate_element = function(element) {
        var height = get_attr(element, 'height');
        var width = get_attr(element, 'width');
        var x = get_attr(element, 'x');
        var y = get_attr(element, 'y');
        var strokewidth = get_attr(element, 'stroke-width');

        var on = function(offset) {
            set_attr(element, "height", height+offset);
            set_attr(element, "width", width+offset);
            set_attr(element, "x", x-offset/2);
            set_attr(element, "y", y-offset);
            set_attr(element, "stroke-width", strokewidth+offset);
        };

        var count = 0;
        var rising = true;
        var pulse = function() {
            count += rising ? 2 : -2;
            on(count);

            if (rising && count > 4) {
                rising = false;
            } else if (!rising && count < 0) {
                rising = true;
            }
        };

        var id = setInterval(pulse, 75);
        return function() {
            clearInterval(id);
            on(0);
        };
    };

    var highlight_target = function(layer, id) {
        // this won't work on ie < 8
        var el = document.getElementById(layer.id+'_root');
        var placemark = $(el);
        var target = $('#'+id + ', .'+id);

        if (placemark && target) {
            placemark.hover(
                function() {
                    target.toggleClass("groupSelection", true);
                },
                function() {
                    target.toggleClass("groupSelection", false);
                }
            );

            target.hover(
                function() {
                    force_topmost(layer);
                    pulsate(layer, true);
                },
                function() {
                    pulsate(layer, false);
                }
            );
        }
    };

    layer.events.on({"loadend":function(){
        if (zoom) zoom_to(layer);
        link_layer(layer, url);
        highlight_target(layer, id);
    }});

    return layer;
};