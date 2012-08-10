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
        $(document.getElementById(layer.id+'_root')).css('cursor', 'pointer')
    }});

    return layer;
};