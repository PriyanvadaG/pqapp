#!/usr/bin/env python3
import io
import pytz
import dateutil.parser
from dateutil.relativedelta import relativedelta
from datetime import date
import datetime as dt

import pandas as pd
import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import plotly.express as px

from common import app, gcs_client, bucket

# from .layout import html_layout


FILE_CACHE = {}
MT_TZ = pytz.timezone("Canada/Mountain")



def blobname_to_uri(blobname):
    return f"gs://{app.config['CLOUD_STORAGE_BUCKET']}/{blobname}"


def blobname_to_datetime(blobname):
    datetimes_str = blobname[len(f"{app.config['FOLDER_NAME']}/output"):]
    dt_str_1st = datetimes_str[:datetimes_str.index("Z")+1]
    dt_str_2nd = datetimes_str[datetimes_str.index("Z")+2:]
    dt_str_2nd = dt_str_2nd[:dt_str_2nd.index("Z")+1]
    return dateutil.parser.parse(dt_str_1st).replace(tzinfo=MT_TZ),\
        dateutil.parser.parse(dt_str_2nd).replace(tzinfo=MT_TZ)


def blobname_to_humanname(blobname):
    d1, d2 = blobname_to_datetime(blobname)
    return " <=> ".join([d1.strftime('%Y %b %d(%a), %I:%M.%S%p'),
                         d2.strftime('%Y %b %d(%a), %I:%M.%S%p')])


def blobname_to_timestamp(blobname):
    d1, d2 = blobname_to_datetime(blobname)
    return d1.timestamp(), d2.timestamp()


def init_dashboard(server):
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/graph/',
        external_stylesheets=[
            '/static/dist/css/styles.css',
            'https://fonts.googleapis.com/css?family=Lato'
        ]
    )

    # Custom HTML layout
    # dash_app.index_string = html_layout

    # Create Layout
    # dash_app.layout = html.Div(
    #     children=[dcc.Graph(
    #         id='histogram-graph',
    #         figure=px.histogram(df, x="Frequency", y="Voltage")),
    #     ],
    #     id='dash-container'
    # )
    # TODO: refresh on request, button input
    today = date.today()
    dash_app.layout = html.Div([
        dcc.Store(id='bucket-items-store'),
        html.H1("GRAPHS!"),
        html.Button('Refresh Data', id='refresh-data'),
        dcc.DatePickerRange(
            id='date-picker-range',
            min_date_allowed=today - relativedelta(months=6),
            max_date_allowed=today + dt.timedelta(days=1),
            initial_visible_month=today,
            start_date=today - dt.timedelta(days=7),
            end_date=today,
        ),
        html.Div([html.Div(id='date-selections')]),
        html.Br(),
        html.Div(id='my-output'),
    ])

    @dash_app.callback(
        [Output(component_id='my-output', component_property='children')],
        [Input('list-dropdown', 'value')])
    def update_output_div(blobs):
        print(f"blobs: {blobs}")

        dfs = []
        blobs = blobs or []
        for blob in blobs:
            if blob in FILE_CACHE:
                df = FILE_CACHE[blob]
            else:
                blob_content = io.BytesIO()
                gcs_client.download_blob_to_file(
                    blobname_to_uri(blob), blob_content)

                df = pd.read_csv(
                    io.StringIO(blob_content.getvalue().decode("utf-8")))
                df["label"] = blobname_to_humanname(blob)
                FILE_CACHE[blob] = df
            dfs.append(df)

        if not dfs:
            return [html.Div(
                children=[dcc.Graph(id='histogram-graph')],
                id='dash-graph')]

        df = pd.concat(dfs)
        return [html.Div(
            children=[dcc.Graph(
                id='histogram-graph',
                figure=px.histogram(
                    df,
                    x="Frequency",
                    y="Voltage",
                    color="label"))],
            id='dash-graph')]

    @dash_app.callback(
        [Output(component_id='date-selections', component_property='children')],
        [Input('bucket-items-store', 'data'),
         Input('date-picker-range', 'start_date'),
         Input('date-picker-range', 'end_date')])
    def update_list(data, start_date_str, end_date_str):
        start_date = dateutil.parser.parse(start_date_str).replace(tzinfo=MT_TZ)
        end_date = dateutil.parser.parse(end_date_str).replace(tzinfo=MT_TZ)
        print(start_date)
        print(end_date)
        options = []
        for blob in data:
            blob_start, blob_end = blobname_to_datetime(blob)
            # print(f"{start_date} <= {blob_start} <= {end_date} or {start_date} <= {blob_end} <= {end_date}: {start_date <= blob_start <= end_date or start_date <= blob_end <= end_date:}")
            if start_date <= blob_start <= end_date \
               or start_date <= blob_end <= end_date:
                options.append({'label': blobname_to_humanname(blob),
                                'value': blob})
        return [dcc.Dropdown(
            id="list-dropdown",
            options=options,
            clearable=True,
            multi=True,
        )]

    @dash_app.callback(
        Output('bucket-items-store', 'data'),
        Input('refresh-data', 'n_clicks'))
    def refresh_data(_):
        blobs = [blob.name
                 for blob in gcs_client.list_blobs(bucket)
                 if blob.name.startswith(f'{app.config["FOLDER_NAME"]}/output')]
        return blobs

    return dash_app.server


def create_data_table(df):
    """Create Dash datatable from Pandas DataFrame."""
    table = dash_table.DataTable(
        id='database-table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict(),
        sort_action="native",
        sort_mode='native',
        page_size=300
    )
    return table
