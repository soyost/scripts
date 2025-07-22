#!/usr/bin/env python3

import requests
import argparse
import threading
import time
import datetime
from requests.auth import HTTPBasicAuth
from dash import Dash, dcc, html
from dash.dependencies import Output, Input
import urllib3
import urllib.parse
import pandas as pd
import plotly.graph_objects as go

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

nonprod_urls = [
    "https://rabbitmq-01.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-02.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-03.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-04.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-05.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-06.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-07.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-08.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-09.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-10.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-11.nonprod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-12.nonprod.ord.us.oracle.careaware.net/api/overview"
]

prod_urls = [
    "https://rabbitmq-01.prod.yul.ca.oracle.careaware.net/api/overview",
    "https://rabbitmq-02.prod.yul.ca.oracle.careaware.net/api/overview",
    "https://rabbitmq-01.prod.syd.ap1.oracle.careaware.com/api/overview",
    "https://rabbitmq-02.prod.syd.ap1.oracle.careaware.com/api/overview",
    "https://rabbitmq-01.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-02.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-03.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-04.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-05.prod.ord.us.oracle.careaware.net/api/overview",
    "https://rabbitmq-06.prod.ord.us.oracle.careaware.net/api/overview"
]


def fetch_stats(urls):
    stats = []
    for url in urls:
        base_url = url.split('/api')[0]
        queues_url = f"{base_url}/api/queues"
        try:
            overview_resp = requests.get(url, auth=HTTPBasicAuth('monitor', 'monitor'), verify=False)
            overview_resp.raise_for_status()
            overview = overview_resp.json()

            queues_resp = requests.get(queues_url, auth=HTTPBasicAuth('monitor', 'monitor'), verify=False)
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


def create_figure_plotly(stats, show_ready=True, show_unacked=True):
    cluster_names = [s['cluster_name'] for s in stats]
    ready_vals = [s['ready'] for s in stats]
    unacked_vals = [s['unacked'] for s in stats]
    top_queues = [s['top_queue_name'] for s in stats]

    fig = go.Figure()

    if show_ready:
        fig.add_trace(go.Bar(
            x=cluster_names,
            y=ready_vals,
            name='Ready',
            text=top_queues,
            textposition='none',
            hovertemplate='Cluster: %{x}<br>Ready: %{y}<br>Top Queues: %{text}<extra></extra>',
        ))

    if show_unacked:
        fig.add_trace(go.Bar(
            x=cluster_names,
            y=unacked_vals,
            name='Unacked',
            text=top_queues,
            textposition='none',
            hovertemplate='Cluster: %{x}<br>Unacked: %{y}<br>Top Queues: %{text}<extra></extra>',
        ))

    fig.update_layout(
    title='OKE RabbitMQ Cluster Overview',
    xaxis_title='Cluster',
    yaxis_title='Messages',
    barmode='group',
    width=1000,
    height=600,
    hoverlabel=dict(
        bgcolor="white",
        font_size=12,
        font_color="black"
    )
)


    return dcc.Graph(figure=fig)


def run_dash(urls):
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("RabbitMQ Cluster Overview"),
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
        html.Div(id='bar-chart'),
        html.Div(id='top-queues-links', style={'marginTop': '30px'}),
        dcc.Interval(id='interval', interval=30*60*1000, n_intervals=0)
    ])

    @app.callback(
        Output('bar-chart', 'children'),
        Output('top-queues-links', 'children'),
        Input('interval', 'n_intervals'),
        Input('message-type-filter', 'value')
    )
    def update_graph(n, selected):
        stats = fetch_stats(urls)
        fig = create_figure_plotly(
            stats,
            show_ready='ready' in selected,
            show_unacked='unacked' in selected
        )

        # Build the top queues links
        links = []
        for s in stats:
            cluster_url = None
            for url in prod_urls + nonprod_urls:
                if s["cluster_name"] in url:
                    cluster_url = url.split('/api')[0]
                    break
            if not cluster_url:
                continue

            queue_names = s["top_queue_name"].replace("• ", "").split("<br>")
            for q in queue_names:
                q = q.strip()
                if q.lower() != "none":
                    encoded_q = urllib.parse.quote(q, safe='')
                    link = f"{cluster_url}/#/queues/%2F/{encoded_q}"
                    links.append(html.Li(html.A(q, href=link, target="_blank")))

        return fig, html.Ul(links)

    app.run(debug=False, use_reloader=False, port=8051)


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
