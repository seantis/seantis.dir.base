if (!seantis) seantis = {};

 $(window).on('maploadend', function(e, widget) {

    var placemarks = (function(map) {
        var result = [];
        for (var i = 0; i < map.layers.length; i++) {
            if (typeof map.layers[i].attributes === 'undefined') continue;
            if (typeof map.layers[i].attributes.is_placemark === 'undefined') {
                continue;
            }

            result.push(map.layers[i]);
        }
        return result;
    })(widget.map);

    var force_topmost = function(layer) {
        var parent = document.getElementById(layer.id + '_vroot');
        if (!parent) return;

        // append the container holding the marker to the container holding
        // all the markers, forcing it to show on top of the other markers (
        // essentially what you would usually do with a z-index).

        // SVG's render orders is defined solely through element order, which
        // is why this is done like that, see:

        // http://stackoverflow.com/questions/482115/
        // with-javascript-can-i-change-the-z-index-layer-of-an-svg-g-element

        parent.parentNode.parentNode.appendChild(parent.parentNode);
    };

    var pulsate = function(layer, start) {
        var parent = document.getElementById(layer.id + '_vroot');
        if (!parent) return;

        if (typeof parent.stop_animation !== 'undefined') {
            parent.stop_animation();
            delete parent.stop_animation;
        }

        if (! start) return;

        var elements = parent.childNodes;
        var stops = [];
        for (var i = 0; i < elements.length; i++) {
            stops[i] = pulseate_element(elements[i]);
        }
        parent.stop_animation = function() {
            for (var i = 0; i < stops.length; i++) {
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

    var pulseate_element = function(element) {
        var height = get_attr(element, 'height');
        var width = get_attr(element, 'width');
        var x = get_attr(element, 'x');
        var y = get_attr(element, 'y');
        var strokewidth = get_attr(element, 'stroke-width');

        var on = function(offset) {
            set_attr(element, 'height', height + offset);
            set_attr(element, 'width', width + offset);
            set_attr(element, 'x', x - offset / 2);
            set_attr(element, 'y', y - offset);
            set_attr(element, 'stroke-width', strokewidth + offset);
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

    var get_target = function(layer) {
        var id = layer.attributes.target;
        return $('#' + id + ', .' + id);
    };

    /* setup hover events for targets (results pointing at placemarks) */
    var on_mouse_over_target = function() {
        var layer = $(this).data('layer');
        force_topmost(layer);
        pulsate(layer, true);
    };

    var on_mouse_out_target = function() {
        var layer = $(this).data('layer');
        pulsate(layer, false);
    };

    var on_click_placemark = function() {
        window.location = this.attributes.url;
        return false;
    };

    for (var i = 0; i < placemarks.length; i++) {
        placemarks[i].attributes.target.hover(
            on_mouse_over_target,
            on_mouse_out_target
        );
    }

    /* setup hover events for placemarks */
    var hover_control = new OpenLayers.Control.SelectFeature(placemarks, {
        hover: true,
        highlightOnly: true,
        renderIntent: 'temporary',
        eventListeners: {
            featurehighlighted: function(e) {
                var layer = e.feature.layer;
                layer.attributes.target.toggleClass('groupSelection', true);

                var marker = document.getElementById(layer.id + '_root');
                marker.style.cursor = 'pointer';
            },
            featureunhighlighted: function(e) {
                var layer = e.feature.layer;
                layer.attributes.target.toggleClass('groupSelection', false);
                document.body.style.cursor = 'default';

                var marker = document.getElementById(layer.id + '_root');
                marker.style.cursor = 'auto';
            }
        }
    });

    var click_control = new OpenLayers.Control.SelectFeature(placemarks, {
        hover: false,
        highlightOnly: true,
        renderIntent: 'temporary',
        eventListeners: {
            featurehighlighted: function(e) {
                var layer = e.feature.layer;
                window.location = layer.attributes.url;
            }
        }
    });

    widget.map.addControl(hover_control);
    widget.map.addControl(click_control);

    hover_control.activate();
    click_control.activate();

});

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
        projection: new OpenLayers.Projection('EPSG:4326')
    });

    layer.attributes = {
        'is_placemark': true,
        'target_id': id,
        'target': $('#' + id + ', .' + id),
        'letter': letter,
        'url': url
    };

    var zoom_to = function(layer) {
        var zoom = layer.map.getZoom();
        layer.map.zoomToExtent(layer.getDataExtent());
        layer.map.zoomTo(zoom);
    };

    if (zoom) {
        layer.events.on({
            'loadend': function() {
                zoom_to(layer);
            }
        });
    }

    layer.attributes.target.data('layer', layer);

    return layer;
};
