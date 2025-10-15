#!/usr/bin/env python3
import requests
from dash import Dash, dcc, html
import plotly.graph_objs as go

# ---------------------------
# Step 1: Fetch COVID data
# ---------------------------
def get_covid_data():
    url = "https://disease.sh/v3/covid-19/countries/usa"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {
            "Cases": data["cases"],
            "Today Cases": data["todayCases"],
            "Deaths": data["deaths"],
            "Today Deaths": data["todayDeaths"],
            "Recovered": data["recovered"],
            "Active": data["active"]
        }
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return {}

# Fetch once at start
covid_data = get_covid_data()
labels = list(covid_data.keys())
values = list(covid_data.values())

# ---------------------------
# Step 2: Create Dash app
# ---------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.H1("COVID-19 Stats: USA", style={'textAlign': 'center'}),
    
    dcc.Tabs([
        dcc.Tab(label='Bar Chart', children=[
            dcc.Graph(
                figure=go.Figure(
                    data=[go.Bar(x=labels, y=values, marker_color="indianred")],
                    layout=go.Layout(title="COVID-19 Metrics (Bar Chart)",
                                     xaxis={"title":"Category"},
                                     yaxis={"title":"Count"})
                )
            )
        ]),
        dcc.Tab(label='Line Chart', children=[
            dcc.Graph(
                figure=go.Figure(
                    data=[go.Scatter(x=labels, y=values, mode="lines+markers", line=dict(color="blue"))],
                    layout=go.Layout(title="COVID-19 Metrics (Line Chart)",
                                     xaxis={"title":"Category"},
                                     yaxis={"title":"Count"})
                )
            )
        ]),
        dcc.Tab(label='Pie Chart', children=[
            dcc.Graph(
                figure=go.Figure(
                    data=[go.Pie(labels=labels, values=values, hole=0.3)],
                    layout=go.Layout(title="COVID-19 Metrics (Pie Chart)")
                )
            )
        ])
    ])
])

# ---------------------------
# Step 3: Run server
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8051, debug=True, dev_tools_hot_reload=False)
