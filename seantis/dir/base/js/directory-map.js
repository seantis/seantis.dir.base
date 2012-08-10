if (!seantis) seantis = {};

seantis.maplayer = function(id, url, title, letter, zoom) {
    var kmlurl = url + '@@kml-document?letter=' + letter;

    console.log(kmlurl);
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

    if (zoom) {
        layer.events.on({"loadend":function(){
            layer.map.zoomToExtent(layer.getDataExtent());
            if(layer.features.length>1){
                layer.map.zoomTo(layer.map.getZoom()-1);
            } else {
                layer.map.zoomTo(layer.map.getZoom()-4);
            }
        }});
    }

    return layer;
};