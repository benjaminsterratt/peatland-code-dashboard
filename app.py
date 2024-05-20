from shiny import module, ui, reactive, render, App, run_app
from shinywidgets import output_widget, render_widget

import pandas as pd

import plotly.colors as co
import plotly.graph_objects as go

#%% INPUTS

DATA = pd.read_csv("data.csv", keep_default_na = False)

DATA["Country"] = DATA["Country"].astype(pd.CategoricalDtype(["England", "Scotland", "Wales", "Northern Ireland"], ordered = True))
DATA["Status"] = DATA["Status"].astype(pd.CategoricalDtype(["Under Development", "Validated", "Restoration Validated"], ordered = True))

GROUPING_COLUMNS = ["Country", "Status", "PIU Issuance", "Developer", "Validator"]

#%% PRE-PROCESSING

CHOICES = {column: list(DATA[column].sort_values().unique()) for column in GROUPING_COLUMNS}

COLOUR_PALETTE = {column: {(CHOICES[column] + ["Other"])[i]: co.DEFAULT_PLOTLY_COLORS[i % len(co.DEFAULT_PLOTLY_COLORS)] for i in range(0, len(CHOICES[column]) + 1)} for column in GROUPING_COLUMNS}

#%% MODULES

#%%% FILTER

@module.ui
def filter_ui(choices, title):
    elements = [
        ui.input_checkbox_group(
            "filter", 
            None, 
            choices,
            selected = choices
            )
        ]
    if len(choices) > 5:
        elements = [
            ui.layout_columns(
                ui.input_action_button("selectAll", "Select all"),
                ui.input_action_button("deselectAll", "Deselect all"),
                style = "margin-bottom: 32px;")
            ] + elements
    return ui.accordion_panel(
        title,
        *elements
        )

@module.server
def filter_server(input, output, session, choices, resetInput = None):
    
    if len(choices) > 5:
    
        @reactive.effect
        @reactive.event(input.selectAll)
        def selectAll():
            ui.update_checkbox_group("filter", selected = choices)
            
        @reactive.effect
        @reactive.event(input.deselectAll)
        def deselectAll():
            ui.update_checkbox_group("filter", selected = [])
            
    if resetInput is not None:
        
        @reactive.effect
        @reactive.event(resetInput)
        def reset():
            ui.update_checkbox_group("filter", selected = choices)
            
    return input.filter

#%% UI

userInterface = ui.page_sidebar(
    ui.sidebar(
        ui.accordion(
            ui.accordion_panel("Breakdown",
                               ui.input_radio_buttons("breakdown", None, GROUPING_COLUMNS),
                               ),
            ui.accordion_panel("Filters",
                               ui.input_action_button("resetFilters", "Reset filters", style = "margin-left: 20px; margin-right: 20px; margin-bottom: 32px;"),
                               ui.accordion(
                                   *[filter_ui(column.replace(" ", "_"), CHOICES[column], column) for column in GROUPING_COLUMNS],
                                   open = False)
                               ),
            open = True),
        width = 420, title = "Peatland Code Dashboard"),
    ui.head_content(ui.tags.style(".plotly-notifier {display: none;}", method = "inline")),
    ui.layout_columns(
        ui.layout_columns(
            ui.card(
                ui.card_header("Carbon Pathway"),
                output_widget("carbonPathway")
                ),
            ui.card(
                ui.card_header("Key Statistics")
                ),
            ui.card(
                ui.card_header("Area Breakdown"),
                output_widget("areaBreakdown")
                ),
            col_widths = [12, 6, 6]),
        ui.navset_card_pill(
            ui.nav_panel("List",
                         ui.output_data_frame("projectList")
                         ),
            ui.nav_panel("Map"),
            title = "Projects"),
        col_widths = [8, 4]),
    fillable = True)

#%% SERVER

def server(input, output, session):

    filters = {}
    for column in GROUPING_COLUMNS:
        filters[column] = filter_server(column.replace(" ", "_"), CHOICES[column], input.resetFilters)
        
    @reactive.calc
    def data():
        data = DATA.copy()
        for column in filters:
            data = data[data[column].isin(filters[column]())]
        return data
    
    @render_widget
    def carbonPathway():
        df = data().copy()
        order = df.groupby(input.breakdown(), observed = True)["Claimable Emission Reductions"].sum().sort_values(ascending = False).reset_index()[input.breakdown()].to_list()
        if len(order) > 5:
            order = order[0:5]
            df[input.breakdown()] = df[input.breakdown()].where(df[input.breakdown()].isin(order), "Other")
            order.append("Other")
        df["Year"] = [list(range(df["Start Year"].min() - 1, df["End Year"].max() + 2)) for i in range(0, len(df))]
        df = df.explode("Year")
        df["Claimable Emission Reductions"] = (df["Claimable Emission Reductions"] / df["Duration"]).where((df["Year"] >= df["Start Year"]) & (df["Year"] <= df["End Year"]), 0)
        df = df.groupby(["Year", input.breakdown()], observed = True)["Claimable Emission Reductions"].sum().reset_index().sort_values("Year")
        df["Claimable Emission Reductions"] = df.groupby(input.breakdown(), observed = True)["Claimable Emission Reductions"].cumsum()
        return go.Figure(
            data = [
                go.Scatter(
                    x = df.loc[df[input.breakdown()] == value, "Year"],
                    y = df.loc[df[input.breakdown()] == value, "Claimable Emission Reductions"],
                    stackgroup = "default",
                    name = value,
                    marker = {"color": COLOUR_PALETTE[input.breakdown()][value]},
                    hovertemplate = "%{y:.3s}"
                    )
                for value in order],
            layout = go.Layout(
                xaxis = {"title_text": "Year"},
                yaxis = {"title_text": "Predicted claimable emission reductions (tCO<sub>2</sub>e)"},
                showlegend = True,
                legend = {"title_text": input.breakdown(),
                          "traceorder": "normal",
                          "orientation": "h",
                          "yref": "container"},
                hovermode = "x unified",
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": "autoScale2d"},
                template = "plotly_white"
                )
            )
    
    @render_widget
    def areaBreakdown():
        df = data().copy()
        pass
    
    @render.data_frame
    def projectList():
        return render.DataTable(data()[["Name"]], width = "100%", height = "100%", summary = False)

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)

#%% TODO

#REORGANISE

    #ADD SELECTED PLOT (PIE OF SELECTED (BY BREAKDOWN) vs. UNSELECTED)
    
    #ADD AREA PLOT AS GROUPED (AREA TYPE) + STACKED (AREA SUB-TYPE) BAR (BREAKDOWN) CHART
    
    #DISTRIBUTION PLOT AS RIDGELINE (AREA, DURATION, CARBON EMISSIONS)

    #ADD SHOWCASE (NO. OF PROJECTS, TOTAL AREA, TOTAL CARBON EMISSIONS)
    
#INFO BUTTON, SPECIFICALLY FOR CARBON PATHWAY
