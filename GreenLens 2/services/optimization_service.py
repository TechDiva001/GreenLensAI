import logging
from typing import List, Dict, Any
from services.geospatial_service import haversine_distance

logger = logging.getLogger(__name__)

def optimize_cleanup_route(
    incidents: List[Dict[str, Any]],
    depot_lat: float = 5.6037,
    depot_lon: float = -0.1870,
    truck_capacity: float = 1000.0  # in kg
) -> Dict[str, Any]:
    """
    Optimizes waste collection routing (greedy TSP algorithm) for cleanup vehicles (AI Function #19).
    Calculates environmental impacts (AI Function #20) like fuel saved and CO2 avoided.
    """
    if not incidents:
        return {
            "route_points": [],
            "total_distance_km": 0.0,
            "total_waste_collected_kg": 0.0,
            "capacity_utilization_pct": 0.0,
            "environmental_impact": {
                "distance_saved_km": 0.0,
                "fuel_saved_liters": 0.0,
                "co2_avoided_kg": 0.0,
                "drains_restored": 0
            }
        }
        
    # We assign an estimated waste weight (kg) to each incident based on its blockage & coverage
    # Heuristic: 1% coverage = 5kg of waste
    for inc in incidents:
        cov = inc.get("estimated_waste_coverage", 10)
        inc["estimated_weight_kg"] = round(cov * 5.0, 1)

    # Greedy TSP algorithm
    unvisited = incidents.copy()
    current_lat = depot_lat
    current_lon = depot_lon
    
    route = []
    total_distance = 0.0
    total_weight = 0.0
    
    # Starting depot point
    route_points = [{"point_type": "DEPOT", "latitude": depot_lat, "longitude": depot_lon, "name": "Municipal Depot"}]
    
    while unvisited:
        # Find the nearest incident that fits in the remaining truck capacity
        nearest_idx = -1
        min_dist = float('inf')
        
        for idx, inc in enumerate(unvisited):
            weight = inc.get("estimated_weight_kg", 50.0)
            if total_weight + weight <= truck_capacity:
                dist = haversine_distance(current_lat, current_lon, inc["latitude"], inc["longitude"])
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = idx
                    
        # If no more incidents can fit in the truck, return to depot or stop
        if nearest_idx == -1:
            break
            
        next_inc = unvisited.pop(nearest_idx)
        route.append(next_inc)
        total_distance += min_dist
        total_weight += next_inc.get("estimated_weight_kg", 50.0)
        
        current_lat = next_inc["latitude"]
        current_lon = next_inc["longitude"]
        
        route_points.append({
            "point_type": "REPORT",
            "report_id": next_inc["report_id"],
            "latitude": next_inc["latitude"],
            "longitude": next_inc["longitude"],
            "waste_weight_kg": next_inc["estimated_weight_kg"],
            "distance_from_prev_m": round(min_dist, 1)
        })
        
    # Return to depot
    return_dist = haversine_distance(current_lat, current_lon, depot_lat, depot_lon)
    total_distance += return_dist
    route_points.append({
        "point_type": "DEPOT_RETURN",
        "latitude": depot_lat,
        "longitude": depot_lon,
        "name": "Municipal Depot",
        "distance_from_prev_m": round(return_dist, 1)
    })
    
    total_distance_km = round(total_distance / 1000.0, 2)
    
    # Environmental impact calculations (AI Function #20)
    # A standard route without optimization is estimated to cover 2.5x more distance
    non_optimized_distance_km = total_distance_km * 2.5
    distance_saved_km = max(0.0, non_optimized_distance_km - total_distance_km)
    
    # Cleanup truck average fuel usage: 0.3 liters per km
    fuel_saved_liters = round(distance_saved_km * 0.3, 1)
    # 1 liter of diesel = 2.68 kg CO2 emissions
    co2_avoided_kg = round(fuel_saved_liters * 2.68, 1)
    
    return {
        "route_points": route_points,
        "total_distance_km": total_distance_km,
        "total_waste_collected_kg": round(total_weight, 1),
        "capacity_utilization_pct": round((total_weight / truck_capacity) * 100.0, 1),
        "environmental_impact": {
            "distance_saved_km": round(distance_saved_km, 2),
            "fuel_saved_liters": fuel_saved_liters,
            "co2_avoided_kg": co2_avoided_kg,
            "drains_restored": len(route)
        }
    }
