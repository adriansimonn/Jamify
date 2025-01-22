# Author: Adrian Simon
# File for handling Spotify Web API requests. Includes functions to fetch tracks and create a desired playlist for the user.
# Contains numerous debug prints that are not visible in the user interface.
# These functions are called in routes.py.

import requests
from flask import current_app

# Searches for existing playlists based on keyphrases extracted from user-inputted description.
def searchForPlaylists(accessToken, keyphrases):
    searchURL = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {accessToken}"}
    playlists = []
    # For each extracted keyphrase from the user description, this code requests 5 playlists from Spotify Web API that match the keyphrase.
    for k in keyphrases:
        # Search parameters for retrieving 5 playlists from spotify for each keyphrase
        parameters = {"q": k, "type": "playlist", "limit": 5}
        try:
            response = requests.get(searchURL, headers=headers, params=parameters)
        except Exception as e:
            print("Failed to fetch playlists as an exception has occurred: {e}")
            return None
        if response.status_code == 200:
            playlists.extend(response.json().get("playlists", {}).get("items", []))
        else:
            print("Error with Spotify API")
            return None
    return playlists

# Takes list of playlists (from searchForPlaylists() function) and other user-inputted settings and returns a list of potential tracks.
# Creates dictionary with every track, counts the frequency of each track across all playlists, sorts them in descending order, and returns the tracks.
# Essentially, the songs that appear most frequently in existing Spotify playlists that match the extracted keyphrases are pushed to the top of the generated playlist.
def getPotentialTracks(accessToken, playlists, numSongs, excludeExplicit):
    tracks = {}
    size = min(numSongs, 100)
    for p in playlists:
        # This avoids invalid playlist entries/playlists with no IDs, as Spotify sometimes returns playlists with "null data" mixed with valid playlists.
        if not isinstance(p, dict):
            print(f"Skipping invalid playlist entry: {p}")
            continue

        playlistID = p.get("id")
        if not playlistID:
            print(f"Skipping playlist with no ID: {p}")
            continue

        tracksURL = f"https://api.spotify.com/v1/playlists/{playlistID}/tracks"
        headers = {"Authorization": f"Bearer {accessToken}"}
        try:
            response = requests.get(tracksURL, headers=headers)
        except Exception as e:
            print("Failed to fetch tracks as an exception has occurred: {e}")
            return None
        # Response status code 200 means the request to Spotify's API was successfully completed.
        # Upon a successful request, tracks are added to the tracks dictionary and their frequency is counted.
        if response.status_code == 200:
            for item in response.json().get("items", []):
                track = item.get("track")
                if track:
                    if excludeExplicit and track.get("explicit", False):
                        continue
                    trackID = track.get("id")
                    if trackID:
                        tracks[trackID] = tracks.get(trackID, 0) + 1
        else:
            print(f"Error fetching tracks for playlist {playlistID}: {response.status_code}")
    
    return sorted(tracks, key=tracks.get, reverse=True)[:size]

# Returns access token for Spotify Web API, this is written as a function due to the fact that the access token is not constant and is unique to each session.
def getTokenFromCode(code):
    tokenUrl = "https://accounts.spotify.com/api/token"
    apiData = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": current_app.config['REDIRECT_URI'],
        "client_id": current_app.config['CLIENT_ID'],
        "client_secret": current_app.config['CLIENT_SECRET'],
    }
    response = requests.post(tokenUrl, data=apiData)
    return response.json().get('access_token')

# Returns Spotify user ID from access token.
def getUserID(accessToken):
    url = "https://api.spotify.com/v1/me"
    headers = {"Authorization": f"Bearer {accessToken}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching user ID: {response.status_code}, {response.text}")
        return None
    userID = response.json().get("id")
    print(f"Fetched User ID: {userID}")
    return userID

# Creates temporary playlist for display of the generated playlist in the user's account, returns the playlistID.
# This playlist is discarded if the user does not like it. (deletePlaylist())
def createTempPlaylist(accessToken, userID):
    url = f"https://api.spotify.com/v1/users/{userID}/playlists"
    headers = {"Authorization": f"Bearer {accessToken}"}
    data = {
        "name": "Generated Playlist",
        "description": "A temporary playlist for previewing. Generated by Jamify",
        "public": False
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 403:
        # When the response status code is 403, this means that Spotify Web API has not authorized the Spotify user to use this app.
        # This is because the app is in development mode, the api mode that allows all users is extended quota mode.
        # Jamify is not in extended quota mode due to the fact that obtaining approval for extended quota mode from Spotify takes several months and has too many design restrictions.
        return "whitelist needed"
    if response.status_code != 201:
        print(f"Error creating playlist: {response.status_code}, {response.text}")
        return None
    playlistID = response.json().get("id")
    print(f"Created Playlist ID: {playlistID}")
    return playlistID

# Takes a playlistID and a list of trackURIs and adds the tracks to the playlist.
def addTracksToPlaylist(accessToken, playlistID, trackURIs):
    url = f"https://api.spotify.com/v1/playlists/{playlistID}/tracks"
    headers = {"Authorization": f"Bearer {accessToken}"}
    data = {"uris": trackURIs}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 201:
        print(f"Error adding tracks to playlist: {response.status_code}, {response.text}")
    else:
        print(f"Tracks added successfully to playlist {playlistID}")

# This function is called when the user approves of the generated playlist and wants to save it to their library.
# Since the playlist is already in their library, the playlist name and description is updated to the user's liking.
# Returns true upon successful playlist update, False otherwise.
def updatePlaylist(accessToken, playlistID, name, description):
    print(f"Updating playlist - Name: {name}, Description: {description}")  # Debug print
    url = f"https://api.spotify.com/v1/playlists/{playlistID}"
    headers = {
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json"
    }
    data = {
        "name": name,
        "description": description
    }
    print(f"Update playlist request data: {data}")  # Debug print
    response = requests.put(url, headers=headers, json=data)
    # Response status code 200 indicates successful update, any other status code indicates an error.
    if response.status_code != 200:
        print(f"Error updating playlist: {response.status_code}, {response.text}")
        return False
    return True

# Deletes playlist from user's library given a playlist ID (generated playlist).
# Returns True upon successful deletion, False if otherwise.
def deletePlaylist(accessToken, playlistID):
    url = f"https://api.spotify.com/v1/playlists/{playlistID}/followers"
    headers = {"Authorization": f"Bearer {accessToken}"}
    response = requests.delete(url, headers=headers)
    # Response status code 200 indicates successful deletion, any other status code indicates an error.
    if response.status_code != 200:
        print(f"Error deleting playlist: {response.status_code}, {response.text}")
        return False
    return True