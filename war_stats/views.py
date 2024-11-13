# from rest_framework.decorators import api_view
# from rest_framework.response import Response
from django.conf import settings
import requests
from urllib.parse import quote
from django.http import JsonResponse
from datetime import datetime
import pytz
from tzlocal import get_localzone  # To detect local timezone

from django.shortcuts import render

def war_stats(request):
    return render(request, 'war_stats/war_stats.html')

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
        # Extract clan and opponent data
        clan_data = data.get("clan", {})
        opponent_data = data.get("opponent", {})
        attacks_per_member = data.get("attacksPerMember", 2)
        
        # Get clan and opponent details
        clan_name = clan_data.get("name", "")
        clan_badge_url = clan_data.get("badgeUrls", {}).get("medium", "")
        clan_total_stars = clan_data.get("stars", 0)
        clan_destruction_percentage = clan_data.get("destructionPercentage", 0)
        
        opponent_name = opponent_data.get("name", "")
        opponent_badge_url = opponent_data.get("badgeUrls", {}).get("medium", "")
        opponent_total_stars = opponent_data.get("stars", 0)
        opponent_destruction_percentage = opponent_data.get("destructionPercentage", 0)
        
        # Initialize breakdown format
        breakdown = {
            "17v17": {"clanStars": "0/0", "opponentStars": "0/0"},
            "16v16": {"clanStars": "0/0", "opponentStars": "0/0"},
            "15v15": {"clanStars": "0/0", "opponentStars": "0/0"},
            "14v14": {"clanStars": "0/0", "opponentStars": "0/0"}
        }
        
        # Count members by town hall level to calculate max attacks
        clan_th_counts = {}
        opponent_th_counts = {}
        
        for member in clan_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            clan_th_counts[th_level] = clan_th_counts.get(th_level, 0) + 1
        
        for member in opponent_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            opponent_th_counts[th_level] = opponent_th_counts.get(th_level, 0) + 1
        
        # Initialize counters for clan and opponent three-star attacks and total attacks per matchup
        matchup_counts = {
            "17v17": {"clanStars": [0, clan_th_counts.get(17, 0) * attacks_per_member], "opponentStars": [0, opponent_th_counts.get(17, 0) * attacks_per_member]},
            "16v16": {"clanStars": [0, clan_th_counts.get(16, 0) * attacks_per_member], "opponentStars": [0, opponent_th_counts.get(16, 0) * attacks_per_member]},
            "15v15": {"clanStars": [0, clan_th_counts.get(15, 0) * attacks_per_member], "opponentStars": [0, opponent_th_counts.get(15, 0) * attacks_per_member]},
            "14v14": {"clanStars": [0, clan_th_counts.get(14, 0) * attacks_per_member], "opponentStars": [0, opponent_th_counts.get(14, 0) * attacks_per_member]}
        }
        
        # Process clan's attacks
        for member in clan_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            for attack in member.get("attacks", []):
                defender_tag = attack.get("defenderTag")
                defender_th_level = next((opponent.get("townhallLevel") for opponent in opponent_data.get("members", []) if opponent["tag"] == defender_tag), None)
                
                if th_level == defender_th_level:
                    matchup_key = f"{th_level}v{th_level}"
                    if matchup_key in matchup_counts:
                        if attack["stars"] == 3:
                            matchup_counts[matchup_key]["clanStars"][0] += 1  # Increment successful 3-star attacks
        
        # Process opponent's attacks
        for member in opponent_data.get("members", []):
            th_level = member.get("townhallLevel", 0)
            for attack in member.get("attacks", []):
                defender_tag = attack.get("defenderTag")
                defender_th_level = next((clan.get("townhallLevel") for clan in clan_data.get("members", []) if clan["tag"] == defender_tag), None)
                
                if th_level == defender_th_level:
                    matchup_key = f"{th_level}v{th_level}"
                    if matchup_key in matchup_counts:
                        if attack["stars"] == 3:
                            matchup_counts[matchup_key]["opponentStars"][0] += 1  # Increment successful 3-star attacks
        
        # Convert counts into the required "x/y" format for the breakdown
        for key, value in matchup_counts.items():
            breakdown[key]["clanStars"] = f"{value['clanStars'][0]}/{value['clanStars'][1]}"
            breakdown[key]["opponentStars"] = f"{value['opponentStars'][0]}/{value['opponentStars'][1]}"
        
        # Prepare the final output structure
        result = {
            "clan": {
                "name": clan_name,
                "badgeUrl": clan_badge_url,
                "totalStars": clan_total_stars,
                "destructionPercentage": clan_destruction_percentage
            },
            "opponent": {
                "name": opponent_name,
                "badgeUrl": opponent_badge_url,
                "totalStars": opponent_total_stars,
                "destructionPercentage": opponent_destruction_percentage
            },
            "breakdown": breakdown
        }

        return result

    except Exception as e:
        return {
            "error": f"An error occurred: {str(e)}"
        } 
