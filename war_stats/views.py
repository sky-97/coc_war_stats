# from rest_framework.decorators import api_view
# from rest_framework.response import Response
from django.conf import settings
import requests
from urllib.parse import quote
from django.http import JsonResponse
from datetime import datetime
import pytz
from tzlocal import get_localzone  # To detect local timezone



def get_war_stats(request, clan_tag):
    try:
        # Prepare Clash of Clans API URL with the plain clan tag
        coc_api_url = f"https://api.clashofclans.com/v1/clans/%23{clan_tag}/currentwar"  # Add %23 manually here

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

        # Lookup dictionaries for opponent and clan TH levels by tag
        opponent_th_levels = {member["tag"]: member.get("townhallLevel", 0) for member in opponent_data.get("members", [])}
        clan_th_levels = {member["tag"]: member.get("townhallLevel", 0) for member in clan_data.get("members", [])}

        # Initialize breakdown data
        breakdown = {
            "17v17": {"clanStars": 0, "opponentStars": 0},
            "16v16": {"clanStars": 0, "opponentStars": 0},
            "15v15": {"clanStars": 0, "opponentStars": 0},
            "14v14": {"clanStars": 0, "opponentStars": 0}
        }

        # Process clan's attacks
        for member in clan_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            for attack in member.get("attacks", []):
                defender_th = opponent_th_levels.get(attack.get("defenderTag"))

                # Count stars for specific TH matchups
                if th_level == 16 and defender_th == 16:
                    breakdown["16v16"]["clanStars"] += attack["stars"]
                elif th_level == 15 and defender_th == 15:
                    breakdown["15v15"]["clanStars"] += attack["stars"]
                elif th_level == 14 and defender_th == 14:
                    breakdown["14v14"]["clanStars"] += attack["stars"]

        # Process opponent's attacks
        for member in opponent_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            for attack in member.get("attacks", []):
                defender_th = clan_th_levels.get(attack.get("defenderTag"))

                # Count stars for specific TH matchups
                if th_level == 16 and defender_th == 16:
                    breakdown["16v16"]["opponentStars"] += attack["stars"]
                elif th_level == 15 and defender_th == 15:
                    breakdown["15v15"]["opponentStars"] += attack["stars"]
                elif th_level == 14 and defender_th == 14:
                    breakdown["14v14"]["opponentStars"] += attack["stars"]

        # Prepare the final output structure without hardcoded names
        result = {
            "clan": {
                "name": clan_data.get("name"),
                "badgeUrl": clan_data.get("badgeUrls", {}).get("medium", ""),
                "totalStars": clan_score,
                "destructionPercentage": clan_percentage
            },
            "opponent": {
                "name": opponent_data.get("name"),
                "badgeUrl": opponent_data.get("badgeUrls", {}).get("medium", ""),
                "totalStars": opponent_score,
                "destructionPercentage": opponent_percentage
            },
            "breakdown": breakdown
        }

        return result

    except Exception as e:
        # Log or handle the exception and return an error message
        return {
            "error": f"An error occurred while calculating war statistics: {str(e)}"
        }
