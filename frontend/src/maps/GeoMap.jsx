import React, {useState,useEffect,useRef} from 'react'
import {MapContainer,TileLayer,CircleMarker,Polyline,Popup,useMapEvents,useMap} from 'react-leaflet'
const GIS_MAP_CENTER = [28.6692, 77.4538]
function MapClickSelector({onSelect}) {
  useMapEvents({click: e => onSelect({latitude: e.latlng.lat, longitude: e.latlng.lng})})
  return null
}
function MapFitPoints({points}) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 14)
    else if (points.length > 1) map.fitBounds(points, {padding:[28,28]})
  }, [map, JSON.stringify(points)])
  return null
}
function GeoMap({pickup,destination,collector=null,routePoints=[],pickable=false,value,onSelect,height=280}) {
  const points = pickable ? (value ? [[value.latitude,value.longitude]] : []) :
    (routePoints.length>1 ? routePoints : [pickup,destination].filter(Boolean).map(p=>[p.latitude,p.longitude]))
  return <div style={{borderRadius:12,overflow:'hidden',border:'1px solid #D8E4F0',marginTop:12}}>
    <MapContainer center={points[0]||GIS_MAP_CENTER} zoom={12} scrollWheelZoom={false}
      style={{height,width:'100%',zIndex:0}}>
      <TileLayer attribution='&copy; OpenStreetMap contributors'
        url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'/>
      <MapFitPoints points={points}/>
      {pickable&&<MapClickSelector onSelect={onSelect}/>}
      {pickable&&value&&<CircleMarker center={[value.latitude,value.longitude]}
        radius={9} pathOptions={{color:'#17324F',fillColor:'#F4BF40',fillOpacity:1}}>
        <Popup>Selected location</Popup>
      </CircleMarker>}
      {!pickable&&pickup&&<CircleMarker center={[pickup.latitude,pickup.longitude]}
        radius={9} pathOptions={{color:'#17324F',fillColor:'#F4BF40',fillOpacity:1}}><Popup>Pickup location</Popup></CircleMarker>}
      {!pickable&&destination&&<CircleMarker center={[destination.latitude,destination.longitude]}
        radius={9} pathOptions={{color:'#17324F',fillColor:'#6FA6E8',fillOpacity:1}}><Popup>NGO receiving location</Popup></CircleMarker>}
      {!pickable&&collector&&<CircleMarker center={[collector.latitude,collector.longitude]} radius={10} pathOptions={{color:'#fff',weight:3,fillColor:'#1E8C79',fillOpacity:1}}><Popup>Latest collector GPS position</Popup></CircleMarker>}
      {!pickable&&routePoints.length>1&&<Polyline positions={routePoints} pathOptions={{color:'#2365AE',weight:4}}/>}
      {!pickable&&pickup&&destination&&routePoints.length<2&&<Polyline positions={points} pathOptions={{color:'#17324F',dashArray:'7 8',weight:3}}/>}
    </MapContainer>
  </div>
}

export default GeoMap
