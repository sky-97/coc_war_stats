from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
import requests
from urllib.parse import quote
from django.http import JsonResponse
from datetime import datetime
import pytz
from tzlocal import get_localzone  # To detect local timezone

def get_war_stats(request, clan_tag):
    try:
        # Check if clan_tag is provided
        if not clan_tag:
            return JsonResponse({"error": "Clan tag is required"}, status=400)

        # URL encode the clan_tag to ensure special characters are handled properly
        encoded_clan_tag = quote(clan_tag)

        # Prepare Clash of Clans API URL
        coc_api_url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/currentwar"

        # Prepare headers with the JWT token from the .env file
        headers = {
            "Authorization": f"Bearer {settings.COC_API_TOKEN}"
        }

        # Fetch data from the Clash of Clans API
        response = requests.get(coc_api_url, headers=headers)

        # Check for invalid or non-existent clan tag (e.g., 404 Not Found)
        if response.status_code == 404:
            return JsonResponse({"error": "Clan tag not found or invalid"}, status=404)

        # Raise an error for other non-200 status codes
        response.raise_for_status()

        # Extract war data from the API response
        war_data = response.json()

        # Calculate statistics based on war_data
        stats = calculate_war_statistics(war_data)

        return JsonResponse(stats)

    except requests.exceptions.RequestException as e:
        # Handle errors from the requests library (e.g., connection errors, timeouts)
        return JsonResponse({"error": f"Request failed: {str(e)}"}, status=500)

    except Exception as e:
        # Catch other errors, including issues with the war data or calculation
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)
    
def calculate_war_statistics(data):
    try:
        # Default values in case keys are missing from data
        clan_data = data.get("clan", {})
        opponent_data = data.get("opponent", {})
        clan_score = clan_data.get("stars", 0)
        opponent_score = opponent_data.get("stars", 0)
        clan_percentage = clan_data.get("destructionPercentage", 0)
        opponent_percentage = opponent_data.get("destructionPercentage", 0)
        end_time_str = data.get("endTime", "")

        total_attack_time = 0
        total_attacks = 0
        ratios = {"16v16": 0, "15v15": 0, "14v14": 0}
        th16v16_stars = 0
        th15v15_stars = 0
        th14v14_stars = 0

        # Lookup dictionaries for opponent and clan TH levels by tag
        opponent_th_levels = {member["tag"]: member.get("townhallLevel", 0) for member in opponent_data.get("members", [])}
        clan_th_levels = {member["tag"]: member.get("townhallLevel", 0) for member in clan_data.get("members", [])}

        # Process clan's attacks
        for member in clan_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            for attack in member.get("attacks", []):
                total_attack_time += attack.get("duration", 0)
                total_attacks += 1
                defender_th = opponent_th_levels.get(attack.get("defenderTag"))

                # Count stars only for specific TH matchups
                if th_level == 16 and defender_th == 16:
                    ratios["16v16"] += 1
                    th16v16_stars += attack["stars"]
                elif th_level == 15 and defender_th == 15:
                    ratios["15v15"] += 1
                    th15v15_stars += attack["stars"]
                elif th_level == 14 and defender_th == 14:
                    ratios["14v14"] += 1
                    th14v14_stars += attack["stars"]

        # Process opponent's attacks
        for member in opponent_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            for attack in member.get("attacks", []):
                total_attack_time += attack.get("duration", 0)
                total_attacks += 1
                defender_th = clan_th_levels.get(attack.get("defenderTag"))

                # Count stars only for specific TH matchups
                if th_level == 16 and defender_th == 16:
                    ratios["16v16"] += 1
                    th16v16_stars += attack["stars"]
                elif th_level == 15 and defender_th == 15:
                    ratios["15v15"] += 1
                    th15v15_stars += attack["stars"]
                elif th_level == 14 and defender_th == 14:
                    ratios["14v14"] += 1
                    th14v14_stars += attack["stars"]

        avg_attack_time = total_attack_time / total_attacks if total_attacks > 0 else 0

        # Convert endTime to local time format based on system's timezone
        if end_time_str: 
            end_time_utc = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S.%fZ")
            utc_zone = pytz.utc
            local_zone = get_localzone()  # Automatically get system's local timezone
            end_time_local = utc_zone.localize(end_time_utc).astimezone(local_zone)
            end_time_local_str = end_time_local.strftime("%Y-%m-%d %H:%M:%S %Z%z")
        else:
            end_time_local_str = "N/A"

        # Return the calculated statistics
        return {
            "clan_score": clan_score,
            "opponent_score": opponent_score,
            "clan_percentage": clan_percentage,
            "opponent_percentage": opponent_percentage,
            "average_attack_time": avg_attack_time,
            "ratios": ratios,
            "th16v16_stars": th16v16_stars,
            "th15v15_stars": th15v15_stars,
            "th14v14_stars": th14v14_stars,
            "end_time_local": end_time_local_str  # Local time formatted end time
        }

    except Exception as e:
        # Log or handle the exception and return an error message
        return {
            "error": f"An error occurred while calculating war statistics: {str(e)}"
        }