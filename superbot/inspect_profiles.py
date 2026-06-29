import requests

url = "https://uabwaeiysyhcebbyatgn.supabase.co/rest/v1/profiles"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVhYndhZWl5c3loY2ViYnlhdGduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNDI5MzAsImV4cCI6MjA5NzcxODkzMH0.uwuvsz5YpuBahkXPPddzLIApJU5ckRIT6IlGAuo4tg4",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVhYndhZWl5c3loY2ViYnlhdGduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNDI5MzAsImV4cCI6MjA5NzcxODkzMH0.uwuvsz5YpuBahkXPPddzLIApJU5ckRIT6IlGAuo4tg4"
}
params = {
    "select": "*",
    "limit": 1
}

response = requests.get(url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    if data:
        print("Columns in profiles:")
        print(data[0].keys())
    else:
        print("Profiles table is empty!")
else:
    print(f"Error: {response.status_code} - {response.text}")
