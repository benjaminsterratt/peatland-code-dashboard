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

AREA_COLOUR_PALETTE = {
    "Blanket Bog": {
        "Near Natural": "rgba(31, 119, 180, 0.3)",
        "Modified": "rgba(31, 119, 180, 0.5)",
        "Drained: Hagg/Gully": "rgba(31, 119, 180, 0.7)",
        "Drained: Artificial": "rgba(31, 119, 180, 0.7)",
        "Actively Eroding: Flat Bare": "rgba(31, 119, 180, 0.9)",
        "Actively Eroding: Hagg/Gully": "rgba(31, 119, 180, 0.9)"
        },
    "Raised Bog": {
        "Near Natural": "rgba(255, 127, 14, 0.3)",
        "Modified": "rgba(255, 127, 14, 0.5)",
        "Drained: Hagg/Gully": "rgba(255, 127, 14, 0.7)",
        "Drained: Artificial": "rgba(255, 127, 14, 0.7)",
        "Actively Eroding: Flat Bare": "rgba(255, 127, 14, 0.9)",
        "Actively Eroding: Hagg/Gully": "rgba(255, 127, 14, 0.9)"
        },
    "Fen": {
        "Modified": "rgba(44, 160, 44, 0.9)"
        },
    "Grassland": {
        "Extensive Drained": "rgba(214, 39, 40, 0.9)",
        "Intensive Drained": "rgba(214, 39, 40, 0.7)"
        },
    "Cropland": {
        "Drained": "rgba(148, 103, 189, 0.9)"
        }
    }

#%% FUNCTIONS

def orderAndTruncateBreakdown(df, breakdown, order, truncate = 5):
    order = df.groupby(breakdown, observed = True)[order].sum().sort_values(ascending = False).reset_index()[breakdown].to_list()
    if len(order) > truncate:
        order = order[0:5]
        df[breakdown] = df[breakdown].where(df[breakdown].isin(order), "Other")
        order.append("Other")
    return df, order

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
                output_widget("carbonPathway"),
                full_screen = True),
            ui.card(
                ui.card_header("Key Statistics"),
                full_screen = True),
            ui.card(
                ui.card_header("Area Breakdown"),
                output_widget("areaBreakdown"),
                full_screen = True),
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
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), "Claimable Emission Reductions")
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
        df = df.melt(input.breakdown(), [column for column in df.columns if column.startswith("Subarea")], "Subarea Type", "Subarea Area")
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), "Subarea Area")
        df[input.breakdown()] = df[input.breakdown()].astype(pd.CategoricalDtype(order, ordered = True))
        df["Area Type"] = df["Subarea Type"].str.replace(".*; (.*);.*", "\\1", regex = True)
        df["Area Type"] = df["Area Type"].astype(pd.CategoricalDtype(df.groupby("Area Type")["Subarea Area"].sum().reset_index().sort_values("Subarea Area")["Area Type"].to_list(), ordered = True))
        df["Subarea Type"] = df["Subarea Type"].str.replace(".*; ", "", regex = True).astype(pd.CategoricalDtype(['Near Natural', 'Modified', 'Drained: Hagg/Gully', 'Drained: Artificial', 'Extensive Drained', 'Intensive Drained', 'Drained', 'Actively Eroding: Flat Bare', 'Actively Eroding: Hagg/Gully'], ordered = True))
        df = df.groupby([input.breakdown(), "Area Type", "Subarea Type"], observed = True)["Subarea Area"].sum().reset_index().sort_values(input.breakdown())
        return go.Figure(
            data = [
                go.Bar(
                    x = df.loc[(df["Area Type"] == row["Area Type"]) & (df["Subarea Type"] == row["Subarea Type"]), "Subarea Area"],
                    y = df.loc[(df["Area Type"] == row["Area Type"]) & (df["Subarea Type"] == row["Subarea Type"]), input.breakdown()],
                    orientation = "h",
                    name = row["Subarea Type"],
                    legendgroup = row["Area Type"],
                    legendgrouptitle_text = row["Area Type"],
                    marker = {"color": AREA_COLOUR_PALETTE[row["Area Type"]][row["Subarea Type"]]},
                    hovertemplate = str(row["Area Type"]) + "<br>" + str(row["Subarea Type"]) + " : %{x:.3s}<extra></extra>"
                    )
                for i, row in df[["Area Type", "Subarea Type"]].drop_duplicates().sort_values(["Area Type", "Subarea Type"], ascending = False).iterrows()],
            layout = go.Layout(
                xaxis = {"title_text": "Area (ha)"},
                yaxis = {"title_text": input.breakdown()},
                barmode = "stack",
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
            
    @render.data_frame
    def projectList():
        return render.DataTable(data()[["Name"]], width = "100%", height = "100%", summary = False)

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)

#%% TODO

#REORGANISE AND EXPAND LAYOUT

    #ADD CARD WITH TABS: SELECTED PLOT (PIE OF SELECTED (BY BREAKDOWN) vs. UNSELECTED) / DISTRIBUTION PLOT AS RIDGELINE (AREA, DURATION, CARBON EMISSIONS)
    
    #ADD AREA PLOT AS GROUPED (AREA TYPE) + STACKED (AREA SUB-TYPE) BAR (BREAKDOWN) CHART
    
    #ADD SHOWCASE (NO. OF PROJECTS, TOTAL AREA, TOTAL CARBON EMISSIONS)
    
#INFO BUTTON, SPECIFICALLY FOR CARBON PATHWAY

#SPEED OPTIMISATION
