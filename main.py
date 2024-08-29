import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy as np

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id='XXXXXXXXXXXXXXXXX',
                                               client_secret='XXXXXXXXXXXXXXXXX',
                                               redirect_uri='http://localhost:3000',
                                               scope="user-library-read playlist-modify-public"))

def get_artist_id(sp: spotipy, name: str) -> str:
    """returns artist id"""
    artist = sp.search(name, 1, 0, "artist")["artists"]["items"]
    if not artist:
        raise Exception(f"Artist {name} not found.")
    return artist[0]["id"]

def get_artist_album_id(sp: spotipy, artist_id: str, instrument: bool) -> list:
    """returns album ids and the number of tracks"""
    global album_list
    results = sp.artist_albums(artist_id, album_type='album,single')
    albums = results['items']
    while results['next']:
        results = sp.next(results)
        albums.extend(results['items'])

    album_ids = [[], []]

    for album in albums:
        if "instrumental" in album["name"].lower() and not instrument:
            continue
        id = album['id']
        if id not in album_list:
            album_ids[0].append(id)
            album_ids[1].append(album['total_tracks'])
            album_list.append(id)
    
    return album_ids

def get_album_track_ids(sp: spotipy, album_ids: list) -> dict:
    """returns track ids and names on an album"""
    tracks = {}
    for album_id in album_ids:
        results = sp.album_tracks(album_id)['items']
        for track in results:
            tracks[track["id"]] = track["name"]
    return tracks


def album_weight_array(sp: spotipy, album_ids: list, track_numbers: list) -> np.array:
    """given a list of album ids and numbers of tracks on each album, return a weight array
        based  on whether the user saved the album or not"""
    saved_albums = np.array(sp.current_user_saved_albums_contains(album_ids))
    return np.repeat(saved_albums, np.array(track_numbers)) * 4.7 + 1


def track_pool(sp, artists: list, instrument: bool) -> tuple:
    """"returns {id_1: name_1,... id_n: name_n}, [--weights--]"""
    tracks = {}
    weights = []
    global album_list
    for artist in artists:
        id = get_artist_id(sp, artist)
        album_ids =  get_artist_album_id(sp, id, instrument)
        tracks = tracks | get_album_track_ids(sp, album_ids[0])
        current_weights = album_weight_array(sp, album_ids[0], album_ids[1])
        weights.extend(current_weights / (len(artists) * current_weights.sum()))
    return tracks, weights


def random_tracks(tracks: dict, weights: np.array, total_tracks: int=30) -> np.array:
    """returns an array of randomly chosen track id's"""
    tracks = list(tracks.keys())
    if len(tracks) < total_tracks:
        total_tracks = len(tracks)
    return np.random.choice(tracks, size=total_tracks, replace=False, p=weights)

def make_playlist(sp, track_list: list, name: str) -> None:
    """makes a playlist and adds to user library"""
    user_id = sp.me()["id"]
    playlist = sp.user_playlist_create(user_id, name)
    playlist_id = playlist['id']
    sp.playlist_add_items(playlist_id, track_list)

def run() -> None:
    artists = input("Enter the names of the artists to create a playlist from. Use a comma to separate the names of different artists: \n")
    artists = artists.split(",")

    instruments = input("Include instrumental tracks? (y/n) ")
    if instruments == "y":
        instruments = True
    else:
        instruments = False
    
    try:
        pool = track_pool(sp, artists=artists, instrument=instruments)
    except:
        print("An error occured. Please check the artist name(s) and try again later.")
        return 

    total_tracks = input("How many songs would you like the playlist to contain? Enter a number: ")
    while type(total_tracks) != int:
        try:
            total_tracks = int(total_tracks)
        except: 
            total_tracks = input("Please enter a valid number: ")
    
    regenerate = "y"
    while regenerate == "y":
        track_list = np.array(random_tracks(pool[0], pool[1], total_tracks=total_tracks))
        print("\nHere\'s the playlist: \n")
        for track in list(map(pool[0].get, track_list)):
            print(track)
        regenerate = input("\nRegenerate? (y/n) ")
    
    create_playlist = input("Create playlist and add to library? (y/n) ")
    if create_playlist == "y":
        playlist_name = input("Name your playlist: ")
        make_playlist(sp, track_list, playlist_name)
    return
       

if __name__ == '__main__':
    """Main run execution"""
    album_list = []
    run()