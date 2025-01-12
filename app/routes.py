from flask import Blueprint, redirect, request, session, url_for, current_app, render_template, jsonify
from .spotify import getPotentialTracks, searchForPlaylists, getPreviewURLS, getTokenFromCode, getUserID, createTempPlaylist, addTracksToPlaylist, test_spotify_api
from .gpt_integration import generateKeyphrases

bp = Blueprint('routes', __name__)

@bp.route('/')
def home():
    return render_template('home.html')

@bp.route('/login')
def login():
    scope = " ".join([
        "user-read-private",
        "user-read-email",
        "playlist-modify-public",
        "playlist-modify-private",
        "user-top-read"
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


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('routes.home'))

@bp.route('/callback')
def callback():
    code = request.args.get('code')
    token = getTokenFromCode(code)
    session['access_token'] = token
    return redirect(url_for('routes.create_playlist'))

@bp.route('/generate_playlist')
def generate_playlist():
    accessToken = session.get('access_token')
    if not accessToken:
        return redirect(url_for('routes.login'))
    
    previewURLS = getPreviewURLS(accessToken)
    return {"preview_urls": previewURLS}

@bp.route('/create_playlist', methods=['GET'])
def create_playlist():
    return render_template('playlist_input.html')

@bp.route('/submit_description', methods=['POST'])
def submit_description():
    description = request.form.get('playlistDescription')
    length = request.form.get('playlistSize')
    excludeExplicit = request.form.get('excludeExplicit')
    print(f"Description: {description}, Length: {length}", f"Exclude Explicit: {excludeExplicit}")
    return redirect(url_for('routes.generate_playlist'))

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
        print("No keywords generated.")
        return redirect(url_for('routes.create_playlist'))

    userID = getUserID(accessToken)
    playlistID = createTempPlaylist(accessToken, userID)
    if not playlistID:
        print("Playlist creation failed.")
        return redirect(url_for('routes.create_playlist'))

    playlists = searchForPlaylists(accessToken, keywords)
    tracks = getPotentialTracks(accessToken, playlists, numSongs)
    print("Tracks generated:", tracks)
    trackURIs = [f"spotify:track:{track}" for track in tracks]
    addTracksToPlaylist(accessToken, playlistID, trackURIs)

    print(f"Generated playlist ID: {playlistID}")
    return render_template('playlist_preview.html', playlistID=playlistID)