import requests
import pandas as pd
from datetime import datetime, timedelta
from dash import Dash, html, dcc
import plotly.graph_objs as go
import dash_bootstrap_components as dbc

# --- CONFIG ---
username = "cand5d".lower()
headers = {"User-Agent": "Mozilla/5.0"}

def fetch_bullet_games(username, year, month):
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        games = res.json().get("games", [])
        return [g for g in games if g.get("time_class") == "bullet"]
    except Exception as e:
        print(f"Failed to load {year}-{month:02d}: {e}")
        return []

def extract_daily_stats(games):
    daily = {}
    for g in games:
        try:
            date = datetime.utcfromtimestamp(g["end_time"]).date()
            color = "white" if g["white"]["username"].lower() == username else "black"
            result = g[color]["result"]
            win = 1 if result == "win" else 0
            daily.setdefault(date, {"games": 0, "wins": 0})
            daily[date]["games"] += 1
            daily[date]["wins"] += win
        except:
            continue

    df = pd.DataFrame([
        {"Date": date, "Games": stats["games"], "Wins": stats["wins"]}
        for date, stats in sorted(daily.items())
    ])
    if df.empty:
        print("No bullet games found.")
        return df
    df["Win Rate (%)"] = (df["Wins"] / df["Games"] * 100).round(1)
    df["Flag"] = df["Games"].apply(lambda x: "⚠️ Overuse" if x > 6 else "✅ OK")
    return df

# --- DYNAMIC MONTHS ---
this_month = (2025, 7)  # Known data month
last_month = (2025, 6)

# --- FETCH & COMBINE ---
games_combined = fetch_bullet_games(username, *last_month) + fetch_bullet_games(username, *this_month)
df = extract_daily_stats(games_combined)

# --- DASH APP ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

if not df.empty:
    fig = go.Figure(data=[
        go.Bar(
            x=df["Date"], y=df["Games"],
            name="Games per Day",
            marker_color=['red' if x > 6 else 'green' for x in df["Games"]],
            text=df["Games"], textposition="auto",
            yaxis="y1"
        ),
        go.Scatter(
            x=df["Date"], y=df["Win Rate (%)"],
            name="Win Rate (%)",
            mode='lines+markers',
            line=dict(color="blue"),
            marker=dict(size=10),
            yaxis="y2"
        )
    ])
    layout = go.Layout(
        title="Bullet Games and Win Rate per Day",
        height=500,
        xaxis=dict(title="Date"),
        yaxis=dict(title="Games", side="left"),
        yaxis2=dict(title="Win Rate (%)", side="right", overlaying="y"),
        legend=dict(x=0.1, y=1.1, orientation="h")
    )
else:
    fig = go.Figure(data=[go.Bar(x=[], y=[], name="No Data"), go.Scatter(x=[], y=[], name="No Data")])
    layout = go.Layout(title="No Bullet Games Found", height=500)

app.layout = html.Div([
    html.H1("Bullet Chess Dashboard – Last 2 Months", className="text-center my-4"),
    dcc.Graph(figure={"data": fig.data, "layout": layout}),
    html.H3("Daily Summary Table", className="text-center my-3"),
    dbc.Table.from_dataframe(
        df if not df.empty else pd.DataFrame(columns=["Date", "Games", "Wins", "Win Rate (%)", "Flag"]),
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        style={"textAlign": "center"}
    ) if not df.empty else html.P("No data available.", className="text-center")
], style={"maxWidth": "1200px", "margin": "auto"})

# Save dashboard as HTML
with open("index.html", "w") as f:
    f.write(app.index())
