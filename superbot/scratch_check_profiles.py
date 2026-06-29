import requests

url = "https://uabwaeiysyhcebbyatgn.supabase.co/rest/v1/profiles"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVhYndhZWl5c3loY2ViYnlhdGduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNDI5MzAsImV4cCI6MjA5NzcxODkzMH0.uwuvsz5YpuBahkXPPddzLIApJU5ckRIT6IlGAuo4tg4",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVhYndhZWl5c3loY2ViYnlhdGduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNDI5MzAsImV4cCI6MjA5NzcxODkzMH0.uwuvsz5YpuBahkXPPddzLIApJU5ckRIT6IlGAuo4tg4"
}
params = {
    "select": "id, email, ingest_token, role"
}

response = requests.get(url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    print("Profiles in Supabase:")
    for row in data:
        print(row)
else:
    print(f"Error querying profiles: {response.status_code} - {response.text}")
