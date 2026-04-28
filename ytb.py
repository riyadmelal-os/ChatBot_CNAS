from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import json

API_KEY = "AIzaSyBAYHUhXIjM0sBb-u2AKVPbPTb_TQA7U3A"
youtube = build("youtube", "v3", developerKey=API_KEY)


# ─── SEARCH VIDEOS ─────────────────────────────────────

def search_videos(query, max_results=50):
    results = []

    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=50,
        relevanceLanguage="ar",   # or "fr"
        regionCode="DZ"
    )

    while request and len(results) < max_results:
        response = request.execute()

        for item in response["items"]:
            results.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "date": item["snippet"]["publishedAt"],
                "description": item["snippet"]["description"]
            })

        request = youtube.search().list_next(request, response)

    return results


# ─── TRANSCRIPTS ───────────────────────────────────────

from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(video_id):
    try:
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id, languages=["ar", "fr", "ar-DZ"])
        text = " ".join([t.text for t in fetched])
        return text
    except Exception:
        return None


# ─── COMMENTS ──────────────────────────────────────────

def get_comments(video_id, max_comments=100):
    comments = []

    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            textFormat="plainText"
        )

        while request and len(comments) < max_comments:
            response = request.execute()

            for item in response["items"]:
                top = item["snippet"]["topLevelComment"]["snippet"]
                comments.append(top["textDisplay"])

            request = youtube.commentThreads().list_next(request, response)

    except Exception:
        pass  # comments disabled or restricted

    return comments


# ─── MAIN PIPELINE ─────────────────────────────────────

videos = search_videos("CNAS DZ الصندوق الوطني للتأمينات الاجتماعية")

for video in videos:
    video["transcript"] = get_transcript(video["video_id"])
    video["comments"] = get_comments(video["video_id"])


# ─── SAVE JSON ─────────────────────────────────────────

with open("cnas_youtube_data.json", "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)