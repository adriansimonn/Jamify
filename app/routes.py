# Author: Adrian Simon
# File for handling routes of the application, essentially the brains of the application.
# Connects all pages and scripts together.

from flask import Blueprint, redirect, request, session, url_for, current_app, render_template
from .spotify import getPotentialTracks, searchForPlaylists, getTokenFromCode, getUserID, createTempPlaylist, addTracksToPlaylist, updatePlaylist, deletePlaylist
from .gpt_integration import generateKeyphrases, generatePlaylistName
from flask_mail import Mail, Message

# Initialization of blueprint and mail object. Mail object is used for whitelist requests.
bp = Blueprint('routes', __name__)
mail = Mail()

def init_mail(app):
    mail.init_app(app)

# Default route (home page where users are prompted to log in).
@bp.route('/')
def home():
    return render_template('home.html')

# Login route, allows users to log in through their Spotify accounts.
@bp.route('/login')
def login():
    scope = " ".join([
        "user-read-private",
        "user-read-email",
        "playlist-modify-public",
        "playlist-modify-private",
    ])
    
    authURL = (
        f"https://accounts.spotify.com/authorize?"
        f"client_id={current_app.config['CLIENT_ID']}&"
        f"response_type=code&"
        f"redirect_uri={current_app.config['REDIRECT_URI']}&"
        f"scope={scope}&"
        f"show_dialog=true"
    )
    return redirect(authURL)

# Logout route. Clears session data and redirects to home page.
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('routes.home'))

# Callback route, gets called by Spotify after login is successful.
@bp.route('/callback')
def callback():
    code = request.args.get('code')
    token = getTokenFromCode(code)
    session['access_token'] = token
    return redirect(url_for('routes.create_playlist'))

@bp.route('/create_playlist', methods=['GET'])
def create_playlist():
    return render_template('playlist_input.html')

# Critical function.
# Fetches user inputs from front end, processes description by extracting keyphrases through gpt_integration.py,
# calls all neccessary functions in spotify.py, and generates/displays a playlist for the user.
# Includes robust error handling with redirection to custom error pages for each possible error case.
# Returns redirection to the playlist preview page, passing playlist id and description to the page.
@bp.route('/preview_playlist', methods=['POST'])
def preview_playlist():
    description = request.form.get('playlistDescription')
    numSongs = int(request.form.get('playlistSize'))
    excludeExplicit = request.form.get('excludeExplicit') == 'on'

    accessToken = session.get('access_token')
    if accessToken is None:
        print("Access token missing")
        return redirect(url_for('routes.login'))
    
    keywords = generateKeyphrases(description)
    if keywords == ["none"]:
        print("No keyphrases generated.")
        return render_template('error_processing.html')

    userID = getUserID(accessToken)
    playlistID = createTempPlaylist(accessToken, userID)
    if playlistID == "whitelist needed":
        return render_template('whitelist_form.html')
    if not playlistID:
        return render_template('error_spotify_create.html')

    playlists = searchForPlaylists(accessToken, keywords)
    if playlists is None:
        playlist_id = request.args.get('id')
        access_token = session.get('access_token')
    
        if access_token and playlist_id:
            deletePlaylist(access_token, playlist_id)
        return render_template('error_spotify_fetch.html')

    tracks = getPotentialTracks(accessToken, playlists, numSongs, excludeExplicit)
    if tracks is None:
        playlist_id = request.args.get('id')
        access_token = session.get('access_token')
    
        if access_token and playlist_id:
            deletePlaylist(access_token, playlist_id)
        return render_template('error_spotify_fetch.html')
    
    print("Tracks generated:", tracks)
    trackURIs = [f"spotify:track:{track}" for track in tracks]
    addTracksToPlaylist(accessToken, playlistID, trackURIs)

    print(f"Generated playlist ID: {playlistID}")
    session['playlist_description'] = description
    session['playlist_id'] = playlistID
    return render_template('playlist_preview.html', playlistID=playlistID, description=description)

# This is called when user clicks save to library, followed by back.
# Returns back to playlist preview page, feeding playlist ID for proper displaying.
@bp.route('/return_to_preview/<playlist_id>')
def return_to_preview(playlist_id):
    return render_template('playlist_preview.html', playlistID=playlist_id)

# Calls function in gpt_integration.py to generate a suggested name for playlist from user inputted description and displays
# the playlist naming page with the suggested name offered as an option to the user. (it is autofilled in the name textbox)
@bp.route('/save_playlist/<playlist_id>', methods=['GET'])
def save_playlist_form(playlist_id):
    description = session.get('playlist_description', '')
    suggested_name = generatePlaylistName(description)
    
    return render_template('name_playlist.html', 
                         playlist_id=playlist_id,
                         description=description,
                         suggested_name=suggested_name)

# Renames the playlist title and description by fetching user inputted name from the front end.
# Takes user-inputted description initially used to generate playlist and puts it in description, followed by generated by Jamify.
# Returns playlist successfully saved page.
@bp.route('/save_playlist', methods=['POST'])
def save_playlist():
    playlist_id = request.form.get('playlist_id')
    description = session['playlist_description']
    playlist_name = request.form.get('playlist_name').strip()

    print(f"Debug - Playlist ID: {playlist_id}")  # Debug print
    
    if not playlist_name:
        playlist_name = generatePlaylistName(description)
    
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('routes.login'))
    
    full_description = f"{description}. Playlist generated by Jamify."
    success = updatePlaylist(access_token, playlist_id, playlist_name, full_description)
    
    if not success:
        print("Failed to update playlist")
        
    full_description = f"{description}. Playlist generated by Jamify."
    updatePlaylist(access_token, playlist_id, playlist_name, full_description)
    
    session.pop('playlist_description', None)
    
    return render_template('playlist_success.html')

# Discards playlist, returns playlist discarded page.
@bp.route('/discard_playlist')
def discard_playlist():
    playlist_id = request.args.get('id')
    access_token = session.get('access_token')
    
    if access_token and playlist_id:
        deletePlaylist(access_token, playlist_id)
        session.pop('playlist_description', None)
    
    return render_template('playlist_discarded.html')

# Renders whitelist request form.
@bp.route('/whitelist_request', methods=['GET'])
def whitelist_form():
    return render_template('whitelist_form.html')

# Sends email to developer containing email that has requested to be on whitelist.
# This feature exists due to Spotify Web API's limitations in development mode. Extended quota mode has too many design requirements and takes too long for approval.
@bp.route('/submit_email', methods=['POST'])
def submit_email():
    email = request.form.get('email')
    if not email or email.index("@") == -1:
        return redirect(url_for('/whitelist_request'))

    msg = Message('New Whitelist Request', sender='jamifywhitelist@gmail.com', recipients=['adriansimon477@gmail.com'])
    msg.body = f"New whitelist request received: {email}"
    mail.send(msg)

    return render_template('whitelist_success.html')