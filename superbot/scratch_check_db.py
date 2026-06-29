import requests
import json

url = "https://uabwaeiysyhcebbyatgn.supabase.co/rest/v1/bot_status"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVhYndhZWl5c3loY2ViYnlhdGduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNDI5MzAsImV4cCI6MjA5NzcxODkzMH0.uwuvsz5YpuBahkXPPddzLIApJU5ckRIT6IlGAuo4tg4",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVhYndhZWl5c3loY2ViYnlhdGduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNDI5MzAsImV4cCI6MjA5NzcxODkzMH0.uwuvsz5YpuBahkXPPddzLIApJU5ckRIT6IlGAuo4tg4"
}
params = {
    "select": "*"
}

response = requests.get(url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    print("Bot status entries:")
    if data:
        for row in data:
            print(row)
    else:
        print("No bot status found")
else:
    print(f"Error querying bot_status: {response.status_code} - {response.text}")
