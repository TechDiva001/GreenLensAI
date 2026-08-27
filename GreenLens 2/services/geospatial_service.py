import math
import logging
from typing import Dict, Any, List
from config import KNOWN_DRAINAGE_SEGMENTS

logger = logging.getLogger(__name__)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance between two points in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))
    
    return R * c

def find_nearest_drain_segment(lat: float, lon: float) -> Dict[str, Any]:
    """
    Finds the nearest known drainage segment to the report coordinate
    and categorizes proximity (AI Function #6).
    """
    nearest_segment = None
    min_distance = float('inf')
    
    for segment in KNOWN_DRAINAGE_SEGMENTS:
        dist = haversine_distance(lat, lon, segment["latitude"], segment["longitude"])
        if dist < min_distance:
            min_distance = dist
            nearest_segment = segment
            
    if not nearest_segment:
        return {
            "nearest_segment_id": "UNKNOWN",
            "segment_name": "No segment found",
            "distance_meters": 999.0,
            "proximity_level": "LOW",
            "capacity_restored": 100
        }
        
    distance_meters = round(min_distance, 1)
    
    # Proximity categories from documentation
    if distance_meters <= 5.0:
        proximity_level = "CRITICAL"
    elif distance_meters <= 20.0:
        proximity_level = "HIGH"
    elif distance_meters <= 50.0:
        proximity_level = "MODERATE"
    else:
        proximity_level = "LOW"
        
    return {
        "nearest_segment_id": nearest_segment["segment_id"],
        "segment_name": nearest_segment["name"],
        "distance_meters": distance_meters,
        "proximity_level": proximity_level,
        "capacity_restored": nearest_segment["capacity_restored"]
    }

def detect_waste_hotspots(reports: List[Dict[str, Any]], radius_meters: float = 100.0) -> List[Dict[str, Any]]:
    """
    Clusters reports by GPS coordinates to identify recurring hotspots (AI Function #17 & #12).
    Simple greedy clustering algorithm.
    """
    hotspots = []
    visited_indices = set()
    
    for i, r1 in enumerate(reports):
        if i in visited_indices:
            continue
            
        cluster = [r1]
        visited_indices.add(i)
        
        lat_sum = r1["latitude"]
        lon_sum = r1["longitude"]
        
        for j, r2 in enumerate(reports):
            if j in visited_indices:
                continue
                
            dist = haversine_distance(r1["latitude"], r1["longitude"], r2["latitude"], r2["longitude"])
            if dist <= radius_meters:
                cluster.append(r2)
                visited_indices.add(j)
                lat_sum += r2["latitude"]
                lon_sum += r2["longitude"]
                
        # If multiple reports exist in this cluster, we define a hotspot
        count = len(cluster)
        avg_lat = lat_sum / count
        avg_lon = lon_sum / count
        
        # Heuristics for hotspot naming based on locations/types in cluster
        primary_waste = "mixed"
        if count > 0:
            from collections import Counter
            types = [c.get("waste_type", "mixed") for c in cluster if c.get("waste_type") != "none"]
            if types:
                primary_waste = Counter(types).most_common(1)[0][0]
                
        hotspots.append({
            "hotspot_id": f"HS-{len(hotspots) + 101}",
            "latitude": round(avg_lat, 5),
            "longitude": round(avg_lon, 5),
            "report_count": count,
            "primary_waste_type": primary_waste,
            "severity": "CRITICAL" if count >= 5 else ("HIGH" if count >= 3 else "MODERATE"),
            "description": f"Hotspot containing {count} reports. Primarily {primary_waste} waste."
        })
        
    return hotspots
