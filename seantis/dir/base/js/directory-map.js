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

    layer.events.on({"loadend":function(){
        if (zoom) zoom_to(layer);

        // this won't work on ie < 9 as they are rendered using canvas
        // consider the use of the selectfeature to be compatible
        // or just get rid of the click-functionality on those browsers
        var placemark = $(document.getElementById(layer.id+'_root'));
        if (placemark) {
            placemark.css('cursor', 'pointer');
            placemark.click(function() {
                window.location = url;
                return false;
            });
        }
    }});

    return layer;
};