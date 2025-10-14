#!/usr/bin/env python3

import requests
import argparse
import threading
import time
import datetime
from requests.auth import HTTPBasicAuth
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Output, Input

nonprod_urls = [
    #US_NON_PROD
    "API"
    #NON_PROD_ORD
    "<API>"
    #NON_PROD_JED
    "<API>"
    #NON_PROD_DXB
    "<API>"
]

prod_urls = [
    #PROD_US
    "<API>"
    #PROD_CA
    "<API>",
    #PROD_AP1
    "<API>"
    #PROD_UK
    "<API>"
    #PROD_US_ORD
    "<API>"
]


def fetch_stats(urls):
    stats = []
    for url in urls:
        base_url = url.split('/api')[0]
        queues_url = f"{base_url}/api/queues"
        try:
            overview_resp = requests.get(url, auth=HTTPBasicAuth('<user>', '<password>'))
            overview_resp.raise_for_status()
            overview = overview_resp.json()

            queues_resp = requests.get(queues_url, auth=HTTPBasicAuth('monitor', 'monitor'))
            queues_resp.raise_for_status()
            queues = queues_resp.json()

            if queues:
                top_queues = sorted(
                    queues,
                    key=lambda q: q.get("messages_ready", 0) + q.get("messages_unacknowledged", 0),
                    reverse=True
                )[:3]

                top_queue_names = [q.get("name", "unknown") for q in top_queues]
                top_queue_totals = [
                    q.get("messages_ready", 0) + q.get("messages_unacknowledged", 0) for q in top_queues
        ]
            else:
                top_queue_names = ["none"]
                top_queue_totals = [0]

            stats.append({
                "cluster_name": overview.get("cluster_name", url),
                "ready": overview.get("queue_totals", {}).get("messages_ready", 0),
                "unacked": overview.get("queue_totals", {}).get("messages_unacknowledged", 0),
                "top_queue_name": "• " + "<br>• ".join(top_queue_names),
                "top_queue_total": sum(top_queue_totals)
            })


        except Exception as e:
            print(f"Error with {queues_url}: {e}")
            stats.append({
                "cluster_name": url,
                "ready": 0,
                "unacked": 0,
                "top_queue_name": "error",
                "top_queue_total": 0
            })
    return stats


def create_figure(stats, show_ready=True, show_unacked=True):
    names = [s["cluster_name"] for s in stats]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fig = go.Figure()

    if show_ready:
        fig.add_trace(go.Bar(
            name='Ready Messages',
            x=names,
            y=[s["ready"] for s in stats],
            marker_color='skyblue',
            customdata=list(zip([s["top_queue_name"] for s in stats], [s["top_queue_total"] for s in stats])),
            hovertemplate='<b>%{x}</b><br>Top Queue: %{customdata[0]}<br>Total in Top Queue: %{customdata[1]}<br>Ready: %{y}<extra></extra>'
        ))

    if show_unacked:
        fig.add_trace(go.Bar(
            name='Unacked Messages',
            x=names,
            y=[s["unacked"] for s in stats],
            marker_color='salmon',
            hovertemplate='Unacked: %{y}<extra></extra>'
        ))

    fig.update_layout(
        barmode='stack',
        title=f'RabbitMQ Message Overview<br><sub>Last Refreshed: {now}</sub>',
        xaxis_title='Cluster',
        yaxis_title='Messages',
        margin=dict(t=60, b=120),
        height=600,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_color="black"
        ))
    return fig


def run_dash(urls):
    app = Dash(__name__)
    app.layout = html.Div([
        html.H1("TAS RabbitMQ Cluster Overview"),
        dcc.Checklist(
            id='message-type-filter',
            options=[
                {'label': 'Show Ready Messages', 'value': 'ready'},
                {'label': 'Show Unacked Messages', 'value': 'unacked'}
            ],
            value=['ready', 'unacked'],
            inline=True,
            style={'margin-bottom': '20px'}
        ),
        dcc.Graph(id='bar-chart'),
        dcc.Interval(id='interval', interval=30*60*1000, n_intervals=0)  # refresh every half hour
    ])

    @app.callback(
        Output('bar-chart', 'figure'),
        Input('interval', 'n_intervals'),
        Input('message-type-filter', 'value')
    )
    def update_graph(n, selected):
        stats = fetch_stats(urls)
        return create_figure(
            stats,
            show_ready='ready' in selected,
            show_unacked='unacked' in selected
        )

    app.run(debug=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", action="store_true", help="Use non-production URLs")
    parser.add_argument("-p", action="store_true", help="Use production URLs")
    args = parser.parse_args()

    if args.n:
        urls = nonprod_urls
    elif args.p:
        urls = prod_urls
    else:
        parser.print_help()
        return

    thread = threading.Thread(target=run_dash, args=(urls,), daemon=True)
    thread.start()

    try:
        while True:
            print(f"Refreshed at {datetime.datetime.now()}")
            time.sleep(1800)
    except KeyboardInterrupt:
        print("\nStopped by user. Exiting.")


if __name__ == "__main__":
    main()
