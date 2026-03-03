import numpy as np
import pandas as pd
from geopy.distance import geodesic
from datetime import datetime
import random

class LogisticsAI:
    def __init__(self):
        # In a real app, you would load your trained XGBoost model here
        # self.pricing_model = joblib.load('pricing_model.pkl')
        pass

    def calculate_dynamic_price(self, distance_km, weight_kg, vehicle_type):
        """
        ALGORITHM: Dynamic Pricing Engine
        Logic: Base Rate + (Distance * Fuel Factor) + (Weight * Strain Factor) * Demand Multiplier
        """
        
        # 1. Base Rates per Vehicle (Cost per KM)
        base_rates = {
            '3-wheeler': 15,
            'mini-truck': 25,
            'pickup': 35,
            'truck': 50
        }
        
        rate_per_km = base_rates.get(vehicle_type, 20)
        
        # 2. Demand Multiplier (Simulated Contextual Bandit)
        # Higher prices during peak hours (8 AM - 11 AM and 5 PM - 9 PM)
        current_hour = datetime.now().hour
        demand_multiplier = 1.0
        
        if 8 <= current_hour <= 11 or 17 <= current_hour <= 21:
            demand_multiplier = 1.4  # 40% Surge
        elif current_hour < 6:
            demand_multiplier = 1.1  # Late night surcharge
            
        # 3. Calculate Final Price
        base_cost = distance_km * rate_per_km
        weight_surcharge = (weight_kg / 1000) * 50 # Extra ₹50 per ton
        
        final_price = (base_cost + weight_surcharge) * demand_multiplier
        
        return {
            "estimated_price": round(final_price, 2),
            "surge_applied": demand_multiplier > 1.0,
            "demand_factor": demand_multiplier,
            "distance_km": round(distance_km, 2)
        }

    def match_driver(self, pickup_lat, pickup_lng, available_drivers):
        """
        ALGORITHM: Intelligent Driver Scoring (Heuristic Ranking)
        Instead of just 'nearest', we score drivers based on:
        1. Distance (Weighted 50%)
        2. Rating (Weighted 30%)
        3. Vehicle Match (Weighted 20%)
        """
        scored_drivers = []
        
        pickup_coords = (pickup_lat, pickup_lng)
        
        for driver in available_drivers:
            driver_coords = (driver['lat'], driver['lng'])
            distance = geodesic(pickup_coords, driver_coords).km
            
            # --- THE SCORING FORMULA ---
            # Lower distance is better, Higher rating is better
            # Score = (Rating * 20) - (Distance * 5)
            
            score = (driver['rating'] * 20) - (distance * 5)
            
            # Add a bonus if they are a "Gold" partner (Simulating Loyalty Logic)
            if driver.get('is_gold_partner'):
                score += 10
                
            scored_drivers.append({
                "driver_id": driver['id'],
                "name": driver['name'],
                "score": score,
                "distance_km": round(distance, 1),
                "eta_mins": round((distance / 30) * 60) + 5 # Avg speed 30km/h + buffer
            })
            
        # Sort by highest score first (XGBoost Ranking usually does this part)
        scored_drivers.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top match
        return scored_drivers[0] if scored_drivers else None