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
    "https://rmq-03291445-a3bd-4cd7-95e3-b096f4ebbab3.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-151dcb60-9b65-44dc-bdee-865061d41530.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-fb9fb0a8-f980-4cc2-8ea4-282c709b1e11.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-c0883636-f9e4-4089-9bc7-583879fc414d.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-2f230abb-6e0e-4926-9574-404d85be7de6.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-e1c4329e-56ed-4705-9afe-6b29d2133910.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-76432a94-bde9-479b-ad2f-7e725d9a6219.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    #NON_PROD_ORD
    "https://rmq-83cf3621-1276-46bf-ab07-bdaeb2fa7a0b.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-90d16f7b-20bf-432b-8c3e-fbd854f85151.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-d1397b26-12e0-4c7a-85bb-07191e32ecb0.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-4c17f374-3e52-4286-b7f0-06db513ade92.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-14245fd4-1252-48ce-a2ff-a85cb2582e02.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-54fa602b-5a3d-425f-a68d-a155c0b6bf2b.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-3c5de38b-45cc-4fef-b004-e3335e1b9753.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    #NON_PROD_JED
    "https://rmq-d408e20d-d32b-4395-87e7-c1f7cefeb4f1.sys.prod.rths.jed.oci.cernercf.io/api/overview",
    "https://rmq-ad4ee067-421f-431c-bbd1-76335c48468b.sys.prod.rths.jed.oci.cernercf.io/api/overview",
    #NON_PROD_DXB
    "https://rmq-cc71f860-02cb-4ad3-8de6-d7ae4aebc624.sys.prod.rths.dxb.oci.cernercf.io/api/overview",
    "https://rmq-a403c4f4-09db-42b7-96f5-5a26ce401a86.sys.prod.rths.dxb.oci.cernercf.io/api/overview"
]

prod_urls = [
    #PROD_US
    "https://rmq-a00ed26a-ceed-456e-bb6c-004a3577f6b6.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-1e8a1141-510b-4545-8f10-cc07d8fbf46c.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-90eaae2e-24b9-4892-8825-bb36495172d2.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-c314e74d-acfc-4acd-8b55-ff1865d0c92c.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-8ad6cf60-28eb-4b91-b01f-bf09ff2ef028.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-771686b0-3aa4-41ff-8eb6-7f566f1ac104.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-dec92bd5-a7af-49bd-81bb-33344684aaaa.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-a0de305a-3965-4397-b970-36e288d2f002.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-c145c86b-60c5-49e9-a5a1-a6fc3b146b93.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-42032664-26d2-44cc-8271-3ad4ae77b14f.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    "https://rmq-8304f1ff-774c-4188-96bf-73c24e600066.sys.asp2.us-east-2.aws.cernercf.io/api/overview",
    #PROD_CA
    "https://rmq-c8910bf5-7177-4ad3-aebc-3667b5ed7140.sys.asp.ca-central-1.aws.cernercf.io/api/overview",
    "https://rmq-f9dd859a-77c5-4d82-9d9a-c0db1f7432b0.sys.asp.ca-central-1.aws.cernercf.io/api/overview",
    #PROD_AP1
    "https://rmq-943b9068-0091-4744-a618-32edabb6dbd1.sys.asp.ap-southeast-2.aws.cernercf.io/api/overview",
    #PROD_UK
    "https://rmq-1ef49848-a7b3-4838-84c9-938df3a06560.sys.asp.eu-west-2.aws.cernercf.io/api/overview",
    "https://rmq-07190040-ffd4-49c7-93e7-dcac59777641.sys.asp.eu-west-2.aws.cernercf.io/api/overview",
    #PROD_US_ORD
    "https://rmq-51e9f95e-7909-4ffd-a570-050b66aed98b.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-6cdf450c-80a3-4e22-a8df-14f80da84491.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-55afa1d6-8961-4b92-9834-6113ed1f6f94.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-15cdce48-fcd9-4153-b115-aad48d6e92ab.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-4345aadb-9e68-41a6-a661-3cf69e17d1c0.sys.prod.rths.ord.oci.cernercf.io/api/overview",
    "https://rmq-1fd05693-1bd5-4fd4-bc2f-689beacc3a28.sys.prod.rths.ord.oci.cernercf.io/api/overview"
]


def fetch_stats(urls):
    stats = []
    for url in urls:
        base_url = url.split('/api')[0]
        queues_url = f"{base_url}/api/queues"
        try:
            overview_resp = requests.get(url, auth=HTTPBasicAuth('monitor', 'monitor'))
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
