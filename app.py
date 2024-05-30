from shiny import module, ui, reactive, render, App, run_app
from shinywidgets import output_widget, render_widget
from faicons import icon_svg

import pandas as pd

import plotly.colors as co
import plotly.graph_objects as go

#%% INPUTS

DATA = pd.read_csv("data.csv", keep_default_na = False)

DATA["Country"] = DATA["Country"].astype(pd.CategoricalDtype(["England", "Scotland", "Wales", "Northern Ireland"], ordered = True))
DATA["Status"] = DATA["Status"].astype(pd.CategoricalDtype(["Under Development", "Validated", "Restoration Validated"], ordered = True))

GROUPING_COLUMNS = ["Country", "Status", "PIU Issuance", "Developer", "Validator"]

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

#%% PRE-PROCESSING

CHOICES = {column: list(DATA[column].sort_values().unique()) for column in GROUPING_COLUMNS}

COLOUR_PALETTE = {column: {(CHOICES[column] + ["Other"])[i]: co.DEFAULT_PLOTLY_COLORS[i % len(co.DEFAULT_PLOTLY_COLORS)] for i in range(0, len(CHOICES[column]) + 1)} for column in GROUPING_COLUMNS}

#%% FUNCTIONS

def formatNumber(number):
    if number >= 10**6 - 500:
        number = number / 10**6
        suffix = "M"
    elif number >= 10**3:
        number = number / 10**3
        suffix = "k"
    else:
        suffix = ""
    return f"{number:.3g}{suffix}"

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

#%%% VALUE BOXES

@module.ui
def valueBoxes_ui(highlight = None):
    theme = [None, None, None]
    if highlight is not None:
        theme[highlight - 1] = "primary"
    return ui.layout_columns(
        ui.value_box("Projects", ui.output_text("updateProjects"), "peatland restoration projects.", theme = theme[0], showcase = icon_svg("arrow-up-from-ground-water")),
        ui.value_box("Area", ui.output_text("updateArea"), "of peatland set for restoration.", theme = theme[1], showcase = icon_svg("ruler-combined")),
        ui.value_box("Carbon", ui.output_text("updateCarbon"), "of predicted claimable emission reductions.", theme = theme[2], showcase = icon_svg("temperature-arrow-down"))
        )

@module.server
def valueBoxes_server(input, output, session, data):
        
    @render.text
    def updateProjects():
        return formatNumber(len(data()))

    @render.text
    def updateArea():
        return formatNumber((data()["Area"].sum())) + " ha"
    
    @render.text
    def updateCarbon():
        return formatNumber(data()["Claimable Emission Reductions"].sum()) + " tCO₂e"

#%% UI

userInterface = ui.page_navbar(
    ui.nav_spacer(),
    ui.nav_panel(
        #PROJECTS MAP (NON-BREAKDOWN) -> LINK TO PROJECTS TAB
        #AREA SUNBURST (NON-BREAKDOWN) -> LINK TO AREA TAB
        #CARBON PATHWAY (NON-BREAKDOWN) -> LINK TO CARBON TAB
        "Overview",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_overview"),
            ui.card(),
            ui.card(),
            ui.card(),
            col_widths = [12, 4, 4, 4], row_heights = [2, 7])
        ),
    ui.nav_panel(
        #PROJECT LIST/MAP
        #SELECTED PROJECT INFORMATION + PLOTS
        "Projects",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_projects", 1),
            ui.navset_card_pill(
                ui.nav_panel("List",
                             ui.output_data_frame("projectList")
                             ),
                ui.nav_panel("Map"),
                title = "Projects"),
            ui.card(),
        col_widths = [12, 6, 6], row_heights = [2, 7])
        ),
    ui.nav_panel(
        #AREA BREAKDOWN
        #AREA DISTRIBUTION PLOT
        "Area",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_area", 2),
            ui.card(
                ui.card_header("Breakdown"),
                output_widget("areaBreakdown"),
                full_screen = True),
            ui.card(),
            col_widths = [12, 8, 4], row_heights = [2, 7])
        ),
    ui.nav_panel(
        #CARBON PATHWAY
        #CARBON DISTRIBUTION PLOT
        "Carbon",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_carbon", 3),
            ui.card(
                ui.card_header("Pathway"),
                output_widget("carbonPathway"),
                full_screen = True),
            ui.card(),
            col_widths = [12, 8, 4], row_heights = [2, 7])
        ),
    title = "Peatland Code Dashboard",
    sidebar = ui.sidebar(
            output_widget("simpleProjectBreakdown"),
            ui.accordion(
                ui.accordion_panel("Breakdown",
                                   ui.input_radio_buttons("breakdown", None, GROUPING_COLUMNS),
                                   ),
                ui.accordion_panel("Filters",
                                   ui.output_ui("resetFilters"),
                                   ui.accordion(
                                       *[filter_ui(column.replace(" ", "_"), CHOICES[column], column) for column in GROUPING_COLUMNS],
                                       open = False)
                                   ),
                open = True),
            width = 420),
    fillable = True,
    header = ui.head_content(ui.include_css("app.css"))
    )

#%% SERVER

def server(input, output, session):

    #%%% SIDEBAR    

    filters = {}
    for column in GROUPING_COLUMNS:
        filters[column] = filter_server(column.replace(" ", "_"), CHOICES[column], input.resetFilters)
    
    enableResetFilter = reactive.value(False)
    
    @reactive.calc
    def data():
        data = DATA.copy()
        filtered = False
        for column in filters:
            selected = filters[column]()
            if len(selected) != len(CHOICES[column]):
                filtered = True
                data = data[data[column].isin(selected)]
        enableResetFilter.set(filtered)
        return data
    
    @render.ui
    def resetFilters():
        if enableResetFilter.get():
            return ui.input_action_button("resetFilters", "Reset filters", style = "margin-bottom: 16px;")
        else:
            return ui.input_action_button("resetFilters", "Reset filters", style = "margin-bottom: 16px;", disabled = "")

    @render_widget
    def simpleProjectBreakdown():
        df_unselected = DATA.copy()
        df_unselected["Unselected"] = 1
        df_unselected, order = orderAndTruncateBreakdown(df_unselected, input.breakdown(), "Unselected")
        df_unselected = df_unselected.groupby(input.breakdown(), observed = True)["Unselected"].sum().reset_index()
        df_unselected[input.breakdown()] = df_unselected[input.breakdown()].astype(pd.CategoricalDtype(order, ordered = True))
        df_selected = data().copy()
        df_selected["Selected"] = 1
        if "Other" in order:
            df_selected[input.breakdown()] = df_selected[input.breakdown()].where(df_selected[input.breakdown()].isin(order), "Other")        
        df_selected = df_selected.groupby(input.breakdown(), observed = True)["Selected"].sum().reset_index()
        df_selected[input.breakdown()] = df_selected[input.breakdown()].astype(pd.CategoricalDtype(order, ordered = True))
        df = pd.merge(df_selected, df_unselected, "outer", input.breakdown())
        df["Selected"] = df["Selected"].fillna(0)
        df["Unselected"] = df["Unselected"] - df["Selected"]
        df = df.melt(input.breakdown(), ["Selected", "Unselected"], "Selection Status", "Count")
        df = pd.concat([df.loc[df["Selection Status"] == "Selected"].sort_values(input.breakdown()), df.loc[df["Selection Status"] == "Unselected"].sort_values(input.breakdown(), ascending = False)])
        return go.Figure(
            data = [
                go.Bar(
                    x = [row["Count"]],
                    orientation = "h",
                    marker = {"color": COLOUR_PALETTE[input.breakdown()][row[input.breakdown()]], "pattern_shape": ["" if row["Selection Status"] == "Selected" else "/"], "pattern_fgcolor": "black"},
                    hovertemplate = "<b>" + str(row["Selection Status"]) + "</b><br><i>" + str(row[input.breakdown()]) + "</i><br>%{x}<extra></extra>",
                    hoverlabel = {"bgcolor": "white"}
                    )
                for i, row in df.iterrows()],
            layout = go.Layout(
                xaxis = {"fixedrange": True, "visible": False, "range": [0, df["Count"].sum()]},
                yaxis = {"fixedrange": True, "visible": False},
                barmode = "stack",
                bargap = 0,
                showlegend = False,
                margin = {"autoexpand": False, "l": 17, "r": 17, "t": 0, "b": 0},
                template = "plotly_white",
                height = 60
                )
            )
    
    for page in ["overview", "projects", "area", "carbon"]:
        valueBoxes_server("valueBoxes_" + page, data)
        
    #%%% PROJECTS
    
    @render.data_frame
    def projectList():
        return render.DataTable(data()[["Name"]], width = "100%", height = "100%", summary = False)
    
    #%%% AREA
    
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
                    hovertemplate = "<b>" + str(row["Area Type"]) + "</b><br><i>" + str(row["Subarea Type"]) + "</i><br>%{x:.3s}<extra></extra>",
                    hoverlabel = {"bgcolor": "white"}
                    )
                for i, row in df[["Area Type", "Subarea Type"]].drop_duplicates().sort_values(["Area Type", "Subarea Type"], ascending = False).iterrows()],
            layout = go.Layout(
                xaxis = {"title_text": "Area (ha)"},
                yaxis = {"title_text": input.breakdown()},
                barmode = "stack",
                legend = {"orientation": "h",
                          "yref": "container"},
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
    
    #%%% CARBON
    
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
    
#%% APP

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)

#%% TODO

#ADD CONTEXT TO SIMPLE PROJECT BREAKDOWN, PERHAPS PIVOT TO VERTICAL TO FIX RELAYOUT ISSUES ON SCROLLBAR APPEAR/DISAPPEAR AND MOVE OUT OF SIDEBAR TO LEFT HAND SIDE OF CONTENT AREA

#REORGANISE AND EXPAND LAYOUT

    #ADD CARD WITH TABS: SELECTED PLOT (PIE OF SELECTED (BY BREAKDOWN) vs. UNSELECTED) / DISTRIBUTION PLOT AS RIDGELINE (AREA, DURATION, CARBON EMISSIONS)
    
    #ADD AREA PLOT AS GROUPED (AREA TYPE) + STACKED (AREA SUB-TYPE) BAR (BREAKDOWN) CHART
    
    #ADD SHOWCASE (NO. OF PROJECTS, TOTAL AREA, TOTAL CARBON EMISSIONS)
    
#INFO BUTTON, SPECIFICALLY FOR CARBON PATHWAY

#SPEED OPTIMISATION
