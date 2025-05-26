from dash import html
import dash_bootstrap_components as dbc

def render_all_data_tab(data: dict, max_rows_per_column: int = 50):
    if not isinstance(data, dict):
        return html.Div("Waiting for data...")

    omit_keys = [
        # Add keys you want to exclude from the table
        "WEBSERVER_VIEW_VARIABLES",
        "WEBSERVER_LIST_VARIABLES"
    ]

    highlight_keys = [
        # Add keys you want to highlight for visibility
        "CORE_IODINE_CUMULATIVE",
        "CORE_XENON_CUMULATIVE",
        "CORE_FACTOR"
    ]

    sorted_items = sorted((k, v) for k, v in data.items() if k not in omit_keys)

    table = dbc.Table([
        html.Thead(html.Tr([
            html.Th("Name"),
            html.Th("Value")
        ])),
        html.Tbody([
            html.Tr([
                html.Td(k, style={"backgroundColor": "green"} if k in highlight_keys else {}),
                html.Td(str(v), style={"backgroundColor": "green"} if k in highlight_keys else {})
            ]) for k, v in sorted_items
        ])
    ], bordered=True, hover=True, size="sm", className="table-dark", style={"fontSize": "12px", "width": "100%"})

    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([table]), className="bg-dark border-secondary shadow-sm m-2"), width=12)
        ])
    ], fluid=True)
