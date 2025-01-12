import openai
import json
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def generateKeyphrases(desc):
    messages = [
        {"role": "system", "content": "You are an assistant that extracts keyphrases from descriptions."},
        {"role": "user", "content": f"""
        The goal is to create a Spotify playlist based on a given description, using the Spotify API.
        Generate keyphrases from the given description that can be used to search for existing public playlists on Spotify that would contain the desired songs (songs described by the description).
        Take time to truly understand what the user wants from the short description. Return accurate keyphrases that would show up in the titles or descriptions of playlists that contain the target songs.
        Display the keyphrases separated by commas with no spaces, and display nothing else.
        For example: Description: melodic and euphoric edm music. Your output should look like "euphoric edm, melodic edm". The quotes are there for example, don't include quotes in your answer.
        If the description is empty or nonsense, simply put none as the keyword, do not say anything else. ("none").
        Keep in mind that each keyphrase is individually used to search spotify for playlists that match the description, so make sure each keyphrase is detailed enough for Spotify's search algorithm to know what you are talking about.
        
        Description: {desc}
        """}
    ]

    try:
        rawResponse = openai.ChatCompletion.create(
            model="gpt-4o", 
            messages=messages,
            max_tokens=300,
            temperature=0.5,
        )
        response = rawResponse["choices"][0]["message"]["content"]
        print("GPT Response: ", response)

        keyphrases = response.split(",")
        print("keyphrases: ", keyphrases)
        return keyphrases

    except Exception as e:
        print(f"An error occurred: {e}")
        return None