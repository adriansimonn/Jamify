# Jamify - A Spotify Playlist Generator!
<p align="center">
  <img src="https://raw.githubusercontent.com/adriansimonn/Jamify/refs/heads/main/Logo.jpeg" 
       alt="Jamify System Diagram" 
       width="700">
</p>

Jamify is an AI-powered Spotify playlist generator built with Python & Flask, using OpenAI for natural-language interpretation, the Spotify Web API for discovering and assembling playlists, and Heroku for deployment.
Users describe a their desired playlist in plain English and Jamify generates a personalized playlist using data driven track selection rather than relying on guessing genres or keywords.

## [🎥 Video Demo!](https://drive.google.com/file/d/1dzbnYg9hnm28ix4UWj7Xkb76HB2VM_yC/view?usp=sharing)

## Playlist Generation Flow

<p align="center">
  <img src="https://raw.githubusercontent.com/adriansimonn/Jamify/refs/heads/main/Diagram.png" 
       alt="Jamify System Diagram" 
       width="700">
</p>


### 1. User Input → Searchable Key Phrases (OpenAI API)
The user enters a prompt describing what kind of playlist they want, e.g.:
“I want upbeat songs for studying on a rainy night.”

Jamify sends this prompt to the OpenAI API, which returns 3–7 distilled, high-signal key phrases, such as:

“upbeat study music”, 

“rainy night lofi”, 

“focus beats”

These phrases are optimized for Spotify search.


### 2. Phrase-Based Spotify Playlist Search
Each extracted phrase is used to query the Spotify Web API.
Jamify fetches publicly available playlists that match the input meaning.

For each playlist result, Jamify extracts its track IDs, filtering out duplicates and invalid entries.


### 3. Track Frequency Heap Construction

From all retrieved playlists, every track ID is pushed into a min-heap (scroll to the bottom for an explanation on why I used a min-heap) and hashing is incorporated for O(1) frequency access and updates; track ID is key, frequency is value.

Tracks are counted across all playlists, and the ones frequently appearing across multiple relevant playlists rise to the top.

This ensures the playlist is consensus-driven rather than random.


### 4. Select Top-K Tracks → Generate Playlist Preview

Jamify pops the top K most frequent tracks (e.g., K = 30).
These tracks—ranked by relevance—are added to a temporary playlist via the Spotify Web API, and the user can:

▶️ Preview it


❌ Discard it

💾 Save it permanently to their Spotify library

If saved, the playlist becomes part of the user’s account.

If discarded, Jamify simply regenerates or ends the session nothing is stored server-side!

## Tech Stack
Backend: Python, Flask

APIs: OpenAI API, Spotify Web API

Infra: Heroku Deployment

Frontend: HTML, CSS

Email Service: Flask-Mail (for whitelist requests)

## [🔗 Jamify Link!](https://jamifymusic-a870f58d8b7c.herokuapp.com/)
#### Important Note: Due to limitations with the Spotify Web API's development mode, only 20 whitelisted users are allowed to use Jamify at a time. To get on the whitelist, simply open Jamify and attempt to create a playlist, once prompted, enter your email and you will be added!

## Why a Min-Heap?
When storing items by a certain value (in the case of Jamify, frequency of track IDs), the conventional way to access the elements with the highest values would be to pop from a Max-Heap or use sorting.

#### Here is why I used a min-heap instead:

Min-heap keeps the k largest frequencies by evicting the smallest element when we find a larger one. We only need k items, so we track the "minimum threshold" that makes the top-k cut.

Max-heap would require processing all n items, defeating the purpose.

Min-heaps also have a better time complexity than sorting: O(n log k) vs O(n log n)

With the typical number of track IDs (n) and the user-requested playlist length (k) falling within a certain range on average (n ≈ 250-2000, k ≈ 30-100), we only maintain a heap of size k instead of sorting all n items (Example: n=2000, k=50 → ~13,000 operations vs ~22,000 for full sort).

Min-heaps are also much more space efficient: O(k) heap size instead of O(n) for full sorting. With k capped at 100, heap never exceeds 100 elements regardless of n (which can reach 50,000)


Time complexity: O(n log k) where k << n.

Space complexity: O(n) for frequency map + O(k) for heap.
