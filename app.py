#!/usr/bin/env python
# coding: utf-8




import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import os
import boto3
import json
import io

aws_id = ''
aws_secret = ''
bucket_name = ''
object_key = ''
host = "127.0.0.1"

s3 = boto3.client('s3', aws_access_key_id=aws_id, aws_secret_access_key=aws_secret)
obj = s3.get_object(Bucket=bucket_name, Key=object_key)
data = obj['Body'].read()



#chart1 data
stocks = pd.read_excel(io.BytesIO(data),sheet_name="Selected Index",skiprows=1,parse_dates=True)
stocks.rename({stocks.columns[0]: "Date"},axis=1,inplace=True)
stocks = stocks.set_index(pd.DatetimeIndex(stocks['Date']))





#chart2 data
credit = pd.read_excel(io.BytesIO(data),sheet_name="CalcM"
                      ,skiprows=2,nrows=23,index_col=0)
#remove redundant spaced
credit.index= credit.index.str.strip()

credit=credit.tail(10).transpose()

#calculate series to graph
credit['Total']=100*((credit.iloc[:,2]/credit.shift(periods=12,axis=0).iloc[:,2])-1)
credit['Investment']=100*((credit.iloc[:,3]-credit.shift(periods=12,axis=0).iloc[:,3])/credit.shift(periods=12,axis=0).iloc[:,2])
credit['Cash/Working capital']=100*((credit.iloc[:,4]-credit.shift(periods=12,axis=0).iloc[:,4])/credit.shift(periods=12,axis=0).iloc[:,2])
credit['Other']=100*((credit.iloc[:,5]-credit.shift(periods=12,axis=0).iloc[:,5])/credit.shift(periods=12,axis=0).iloc[:,2])
credit=credit.iloc[:,::-1].iloc[:,:4].dropna()
credit['Year']=credit.index.year





#chart3 data
bank_solvency=pd.read_excel(io.BytesIO(data),sheet_name="B+A"
                      ,skiprows=3,index_col=0).transpose().iloc[1:,:]





#initiate app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server=app.server

#design table of content
url_bar_and_content_div = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

layout_index = html.Div([
    dcc.Link('Navigate to "/page-1"', href='/page-1'),
    html.Br(),
    dcc.Link('Navigate to "/page-2"', href='/page-2'),
    html.Br(),
    dcc.Link('Navigate to "/page-3"', href='/page-3'),
])


#design the layout of page1 with dropdown lists
layout_page_1 = html.Div([    
    html.H1('Page 1'),
    html.Div(id='page-1-content'),
    html.Br(),
    dcc.Link('Go to Page 2', href='/page-2'),
    html.Br(),
    dcc.Link('Go to Page 3', href='/page-3'),
    html.Br(),
    dcc.Link('Go back to home', href='/'),
    dcc.Markdown("""
                  **Financial consitions in France tightened abruptly in March 2020 and have only partially recovered.**
                 """,
                       style={"font":"Segoe UI","fontSize":16}),
    html.Div([

        html.Div([
            html.Label('Index'),
            dcc.Dropdown(
                id='index',
                options=[{"label": x, "value": x} for x in stocks.columns[1:8]],
                multi=True,
                value=stocks.columns[1:8]
            ),
        ],
        style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.Label('MVA Window'),
            dcc.Dropdown(
                id='rolling_window',
                options=[{'label': i, 'value': i} for i in [3,7,14,30]],
                value=7
            ),
        ],style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
    ]),

    dcc.Graph(id='indicator-graphic'),
    
])

#design the layout of page2 with a slider
layout_page_2 = html.Div([
                       html.H1('Page 2'),
                       html.Div(id='page-2-content'),
                       html.Br(),
                       dcc.Link('Go to Page 1', href='/page-1'),
                       html.Br(),
                       dcc.Link('Go to Page 3', href='/page-3'),
                       html.Br(),
                       dcc.Link('Go back to home', href='/'),
                       dcc.Markdown("""
                    **French banks credit to corporates surged amidst the crisis, spurred by the provision of state guaranteed loans.**
                    """,
                       style={"font":"Segoe UI","fontSize":16}),
                       dcc.Graph(id='credit'),
                       dcc.Slider(
                       id='start_year',
                       min=credit['Year'].min(),
                       max=credit['Year'].max(),
                       value=credit['Year'].median(),
                       marks={str(year): str(year) for year in credit['Year'].unique()},
                       step=None
                       )
                      ])

layout_page_3 = html.Div([
                       html.H1('Page 3'),
                       html.Div(id='page-3-content'),
                       html.Br(),
                       dcc.Link('Go to Page 1', href='/page-1'),
                       html.Br(),
                       dcc.Link('Go to Page 2', href='/page-2'),
                       html.Br(),
                       dcc.Link('Go back to home', href='/'),
                       dcc.Markdown("""
                    **France banks are adequately capitalized to withstand the baseline shock but may see material capital depletions in an adverse scenario.**
                    """,
                       style={"font":"Segoe UI","fontSize":16}),
                       dcc.Graph(id='insolvency'),
                       html.Div(id='none',children=[],style={'display': 'none'})
                      ])

# index layout
app.layout = url_bar_and_content_div

# "complete" layout
app.validation_layout = html.Div([
    url_bar_and_content_div,
    layout_index,
    layout_page_1,
    layout_page_2,
    layout_page_3,
])


# Index callbacks
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == "/page-1":
        return layout_page_1
    elif pathname == "/page-2":
        return layout_page_2
    elif pathname == "/page-3":
        return layout_page_3
    else:
        return layout_index



#page1 callback
@app.callback(
    Output('indicator-graphic', 'figure'),
    Input('index', 'value'),
    Input('rolling_window', 'value'))
def update_graph(Index,rolling_window):
    #select stock indexes (by using dropdowon lists) for graphing
    selected_stocks = stocks[Index].rolling(rolling_window,min_periods=1).mean()
    selected_stocks = selected_stocks.loc['2019-12-02':,:]
    #select colors for each line
    colors = ['royalblue','indianred','gold','lightgreen','orange','mediumpurple','lightskyblue']
    fig = go.Figure()
    for i in range(len(Index)):

            fig.add_trace(go.Scatter(x=selected_stocks.index, y=selected_stocks.iloc[:,i], 
                              name = selected_stocks.columns[i],
                              line=dict(color=colors[i], width=3)))
            #change some lines' styles to dash
            fig.for_each_trace(
            lambda trace: trace.update(line=dict(dash="dash", width=3)) if trace.name == "Entertainment" else (),
            )
            fig.for_each_trace(
            lambda trace: trace.update(line=dict(dash="dash", width=3)) if trace.name == "Banks" else (),
            )
            fig.for_each_trace(
            lambda trace: trace.update(line=dict(dash="dash", width=3)) if trace.name == "Hotels, Restaurants & Leisure" else (),
            )
            fig.for_each_trace(
            lambda trace: trace.update(line=dict(dash="dash", width=3)) if trace.name == "Pharmaceuticals" else (),
            )  
    #add title
    fig.update_layout(title_text="France: Stock Indexes by Sectors",
                  font=dict(
                  family="Segoe UI",
                  size=20),
                  legend = dict(font =dict(size=14)),
                  autosize=False,
                  width=1000,
                  height=500,
                  )
    #add subtitle
    fig.add_annotation(
                x = 0.41, y = 1.15, text = "(12/31/2019=100, "+ str(rolling_window)+ " days moving average)", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=18)
                  )
    #add source
    fig.add_annotation(
                x = 0.3, y = -0.2, text = "Source: Bloomberg; and my own calculations.", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=12)
                  )
      
    return fig


#page 2 callback
@app.callback(
    Output('credit', 'figure'),
    Input('start_year', 'value'))
def graph2(start_year):
    credit_selected=credit[credit.Year>=start_year]
    fig=go.Figure()
    for i in credit.columns[:3]:
        fig.add_trace(go.Bar(x=credit_selected.index,y=credit_selected[i],name=i))
    fig.update_layout(barmode='relative', title_text='Bank Credit to Non-financial Corporations',
                     font=dict(
                     family="Segoe UI",
                     size=20),
                     legend = dict(font =dict(size=14)),
                     autosize=False,
                     width=800,
                     height=500,)
    #add 'Total' as line
    fig.add_trace(go.Scatter(x=credit_selected.index,y=credit_selected['Total'],name='Total',
                            line=dict(width=3)))

    
    #add subtitle
    fig.add_annotation(
                x = 0.62, y = 1.15, text = "(Contribution to y-o-y NFC credit growth, percent)", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=18)
                  )
    #add source
    fig.add_annotation(
                x = 0.45, y = -0.2, text = "Source: Haver Analytics; and my own calculations.", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=12)
                  )
    return fig

#page 3 callback
@app.callback(
    Output('insolvency', 'figure'),
    Input('none', 'children'))
def graph3(none):
    fig=go.Figure()
    #create double xaxis label
    x_axis=[['        ','Projected(end-2021)','Projected(end-2021)'],bank_solvency.index]
    
    #create a transparent bar to lift up the other two bars
    fig.add_trace(go.Bar(x=x_axis,y=bank_solvency['Bottom'],name='Bottom',
                         opacity=0,showlegend=False
                        ))
    
    #add error bars to the bottom of 2Q box so create a marker series and minimize 
    #its size to make it invisible
    fig.add_trace(go.Scatter(x=x_axis,y=bank_solvency['Bottom'],name='Bottom1',mode='markers',marker_size=1,
                         opacity=1,showlegend=False,line_color='black',
                         error_y=dict(
                             type='data',
                             symmetric=False,
                             array=[0, 0, 0],
                             arrayminus=bank_solvency['Whisker-']
                         )))
    #add 2Q box
    fig.add_trace(go.Bar(x=x_axis,y=bank_solvency['2Q Box'],name='2Q Box',
                         marker_color='royalblue'
                        ))
    
    #add 3Q box and error bars
    fig.add_trace(go.Bar(x=x_axis,y=bank_solvency['3Q Box'],name='3Q Box',
                    marker_color='limegreen',
                     error_y=dict(
                     type='data',
                     symmetric=False,
                     array=bank_solvency['Whisker+'],
                     arrayminus=[0, 0, 0]
                     )))  
    
    #create 3 markers
    fig.add_trace(go.Scatter(x=x_axis, y=bank_solvency['Mean'],
                    mode='markers', marker_symbol='diamond', marker_color='lightskyblue',
                             marker_line_color="black",marker_line_width=0.5,
                             name='Average'))
    fig.add_trace(go.Scatter(x=x_axis, y=bank_solvency['Weighted average'],
                    mode='markers', marker_symbol='circle', marker_color='yellow',
                             marker_line_color="midnightblue",marker_line_width=0.5,
                             name='Weighted average'))
    fig.add_trace(go.Scatter(x=x_axis, y=bank_solvency['Weighted average (euro area)'],
                    mode='markers', marker_symbol='triangle-up', marker_color='orangered',
                             marker_line_color="midnightblue",marker_line_width=0.5,
                             name='Weighted average (euro area)'))
    #create 3 horizontal lines
    fig.add_trace(go.Scatter(x=x_axis, y=bank_solvency['MDA (11.6%)'],
                             name='MDA (11.6%)',
                    mode='lines', line_dash='dot', line_color='orange'
                            ))
    fig.add_trace(go.Scatter(x=x_axis, y=bank_solvency['Reg. minimum (4.5%) + CCB (2.5%)'],
                             name='Reg. minimum (4.5%) + CCB (2.5%)',
                    mode='lines', line_dash='dashdot', line_color='red'
                            ))
    fig.add_trace(go.Scatter(x=x_axis, y=bank_solvency['Reg. minimum (4.5%)'],
                             name='Reg. minimum (4.5%)',
                    mode='lines', line_dash='dash', line_color='red'
                            ))

    #reformat the layout and add title
    fig.update_layout(barmode='stack', title_text='French Banks—Solvency Stress Test (Baseline & Adverse)',
                     font=dict(
                     family="Segoe UI",
                     size=20),
                     legend = dict(font =dict(size=12)),
                     autosize=False,
                     width=800,
                     height=500,)
    fig.update_xaxes(tickangle=0, tickfont=dict(family='Segoe UI', size=8))
    fig.update_yaxes(tickfont=dict(family='Segoe UI', size=10))
    
    #add subtitle
    fig.add_annotation(
                x = 0.38, y = 1.15, text = "(CET1 Capital Ratio, percent)", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=18)
                  )
    #add source
    fig.add_annotation(
                x = 0.52, y = -0.2, text = "Source: EBA; ECB; ESRB; FitchConnect; and my own calculations.", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=10)
                  )
    #add note
    fig.add_annotation(
                x = 1.2, y = -0.23, 
        text = "Note: The blue and green boxes show the inter-quartile range with whiskers at 5th/95th percentiles. CET1=common equity Tier 1 for 8 French banks.", 
                showarrow = False, xref='paper', yref='paper', 
                xanchor='right', yanchor='auto', xshift=0, yshift=0,
                font=dict(family="Segoe UI",size=10)
                  )
    #pio.write_html(fig, file='figure3.html', auto_open=True)
    return fig



# run app and display result inline in the notebook (can also switch to 'external')
if __name__ == '__main__':
    app.run_server(debug=True,host=host)







