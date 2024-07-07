import re

import pandas as pd

from shiny import module, ui, reactive, render, App, run_app
from shinywidgets import output_widget, render_widget
from faicons import icon_svg

import plotly.colors as co
import plotly.graph_objects as go

#%% INPUTS

DATA = pd.read_csv("data.csv", keep_default_na = False)

DATA["Country"] = DATA["Country"].astype(pd.CategoricalDtype(["England", "Scotland", "Wales", "Northern Ireland"], ordered = True))
DATA["Project Status"] = DATA["Project Status"].astype(pd.CategoricalDtype(["Under Development", "Validated", "Restoration Validated"], ordered = True))

DISPLAY_DATA = DATA.drop(columns = ["ID", "URL", "Latitude", "Longitude"]).rename(columns = {column: " — ".join(column.replace("; ", ";").split(";")[1:]) for column in DATA.columns if column.startswith("Subarea")})
DISPLAY_DATA["Start Year"] = DISPLAY_DATA["Start Year"].where(DISPLAY_DATA["Start Year"] != 2025, None)
DISPLAY_DATA["End Year"] = DISPLAY_DATA["End Year"].where(~DISPLAY_DATA["Start Year"].isna(), None)

BREAKDOWN_COLUMNS = {
    "Country": "country",
    "Project Status": "project status",
    "PIU Status": "PIU status", 
    "Developer": "developer", 
    "Validator": "validator"
    }

CONTINUOUS_COLUMNS = {
    "Area": {
        "UNIT": "ha", 
        "SINGULAR": "area", 
        "PLURAL": "areas",
        "ROUNDING": "3s"
        },
    "Duration": {
        "UNIT": "years", 
        "SINGULAR": "duration", 
        "PLURAL": "durations", 
        "ROUNDING": "0f"},
    "Predicted Emission Reductions": {
        "UNIT": "tCO<sub>2</sub>e", 
        "SINGULAR": "predicted emission reductions", 
        "PLURAL": "predicted emission reductions",
        "ROUNDING": "3s"
        },
    "Predicted Claimable Emission Reductions": {
        "UNIT": "tCO<sub>2</sub>e", 
        "SINGULAR": "predicted claimable emission reductions", 
        "PLURAL": "predicted claimable emission reductions",
        "ROUNDING": "3s"
        }
    }

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

CHOICES = {column: list(DATA[column].sort_values().unique()) for column in list(BREAKDOWN_COLUMNS.keys())}

COLOUR_PALETTE = {column: {(CHOICES[column] + ["Other"])[i]: co.DEFAULT_PLOTLY_COLORS[i % len(co.DEFAULT_PLOTLY_COLORS)] for i in range(0, len(CHOICES[column]) + 1)} for column in list(BREAKDOWN_COLUMNS.keys())}

#%% FUNCTIONS

#%%% UI

def linkedCardHeader(id, text):
    return ui.div(ui.div(text), ui.input_action_link(id, "View more"), style = "display: flex; justify-content: space-between;")

#%%% CALCULATION

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
def filter_ui(title):
    elements = [
        ui.input_checkbox_group(
            "filter", 
            None, 
            CHOICES[title],
            selected = CHOICES[title]
            )
        ]
    if len(CHOICES[title]) > 5:
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
def filter_server(input, output, session, name, filters, resetInput = None):
    
    @reactive.effect
    def updateLabels():
        df = DATA.copy()
        for column in filters:
            if column != name:
                df = df[df[column].isin(filters[column]())]
        df = pd.merge(DATA.copy()[[name]].drop_duplicates(), df[name].value_counts().reset_index().rename(columns = {"index": name, "count": "Count"}), how = "left").sort_values(["Count", name], ascending = [False, True])
        df["Count"] = df["Count"].fillna(0).astype(int)
        ui.update_checkbox_group("filter", choices = {row[name]: row[name] + " (" + str(row["Count"]) + ")" for i, row in df.iterrows()}, selected = input.filter())
    
    if len(CHOICES[name]) > 5:
    
        @reactive.effect
        @reactive.event(input.selectAll)
        def selectAll():
            ui.update_checkbox_group("filter", selected = CHOICES[name])
            
        @reactive.effect
        @reactive.event(input.deselectAll)
        def deselectAll():
            ui.update_checkbox_group("filter", selected = [])
            
    if resetInput is not None:
        
        @reactive.effect
        @reactive.event(resetInput)
        def reset():
            ui.update_checkbox_group("filter", selected = CHOICES[name])
            
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
        ui.value_box("Carbon", ui.output_text("updateCarbon"), "of predicted emission reductions.", theme = theme[2], showcase = icon_svg("temperature-arrow-down"))
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
        return formatNumber(data()["Predicted Emission Reductions"].sum()) + " tCO₂e"
    
#%%% INFO POPOVERS

#%%%% FUNCTIONS

def buildFunction(input, variable, version):
    def function():
        return CONTINUOUS_COLUMNS[getattr(input, re.sub("[^\\w]", "_", variable))()][version]
    function.__name__ = re.sub("[^\\w]", "_", variable)
    return function

#%%%% MODULE

@module.ui
def infoCardHeader_ui(text, popover, variables = None):
    
    outputs = [re.sub("{(.*)}", "\\1", item) for item in re.findall("{[^{}]*}", popover)]
    texts = re.split("{[^{}]*}", popover)
    
    popover = [texts[0]]
    
    if len(outputs) > 0:
        for i in range(0, len(outputs)):
            popover.append(ui.output_text(re.sub("[^\\w]", "_", outputs[i]), inline = True))
            popover.append(texts[i + 1])
        
    buttons = ui.popover(icon_svg("circle-question", height = "14.4px", margin_right = ["0px" if variables is None else "0.2em"]), ui.p(*popover), "Data sourced from ", ui.a("UK Peatland Code Registry", href = "https://mer.markit.com/br-reg/public/index.jsp?entity=project&sort=project_name&dir=ASC&start=0&acronym=PCC&limit=15&additionalCertificationId=&categoryId=100000000000001&name=&standardId=100000000000157"), " in May 2024.")
    
    if variables is not None:
        buttons = ui.div(buttons, ui.popover(icon_svg("gear", height = "14.4px", margin_right = "0px"), *[ui.input_select(re.sub("[^\\w]", "_", variable), ui.tags.b(variable), variables[variable]["Choices"], selected = variables[variable]["Selected"]) for variable in variables]))
    
    return ui.div(ui.div(text), buttons, style = "display: flex; justify-content: space-between;")

@module.server
def infoCardHeader_server(input, output, session, breakdownInput, variables = None):
    
    @render.text
    def breakdown():
        return BREAKDOWN_COLUMNS[breakdownInput()]
    
    if variables is not None:
        for variable in variables:
            render.text(buildFunction(input, variable, variables[variable]))
        return {variable: getattr(input, re.sub("[^\\w]", "_", variable)) for variable in variables}

#%% UI

userInterface = ui.page_navbar(
    ui.nav_spacer(),
    ui.nav_panel(
        #PROJECTS MAP (NON-BREAKDOWN) -> LINK TO PROJECTS TAB
        #AREA TREE MAP (NON-BREAKDOWN) -> LINK TO AREA TAB
        #CARBON PATHWAY (NON-BREAKDOWN) -> LINK TO CARBON TAB
        "Overview",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_overview"),
            ui.card(
                ui.card_header(linkedCardHeader("link_projects", "Projects"))
                ),
            ui.card(
                ui.card_header(linkedCardHeader("link_area", "Area"))
                ),
            ui.card(
                ui.card_header(linkedCardHeader("link_carbon", "Carbon"))
                ),
            col_widths = [12, 4, 4, 4], row_heights = [2, 7]),
        ),
    ui.nav_panel(
        #PROJECT TABLE
        #PROJECT MAP
        #SELECTED PROJECT INFORMATION + PLOTS AS MODAL
        "Projects",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_projects", 1),
            ui.card(
                ui.card_header("Table"),
                full_screen = True),
            ui.card(
                ui.card_header("Map"),
                full_screen = True),
        col_widths = [12, 8, 4], row_heights = [2, 7]),
        value = "projects"),
    ui.nav_panel(
        "Area",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_area", 2),
            ui.card(
                ui.card_header(infoCardHeader_ui("areaBreakdown_header", "Breakdown", "Total area by {breakdown} broken down by type and sub-type.")),
                output_widget("areaBreakdown"),
                full_screen = True),
            ui.card(
                ui.card_header(infoCardHeader_ui("areaDistribution_header", "Distribution", "Distribution of projects' {Y-axis} by {breakdown}.", {"Y-axis": {"Choices": list(CONTINUOUS_COLUMNS.keys()), "Selected": "Area"}})),
                output_widget("areaDistribution"),
                full_screen = True),
            col_widths = [12, 8, 4], row_heights = [2, 7]),
        value = "area"),
    ui.nav_panel(
        "Carbon",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_carbon", 3),
            ui.card(
                ui.card_header(infoCardHeader_ui("carbonPathway_header", "Pathway", "Cumulative {Y-axis} across projects' durations broken down by {breakdown}. Projects without start dates assumed to start in 2025.", {"Y-axis": {"Choices": ["Predicted Emission Reductions", "Predicted Claimable Emission Reductions"], "Selected": "Claimable Emission Reductions"}})),
                output_widget("carbonPathway"),
                full_screen = True),
            ui.card(
                ui.card_header(infoCardHeader_ui("carbonPoints_header", "Points", "Projects' {X-axis} and {Y-axis} broken down by {breakdown}.", {"X-axis": {"Choices": list(CONTINUOUS_COLUMNS.keys()), "Selected": "Duration"}, "Y-axis": {"Choices": list(CONTINUOUS_COLUMNS.keys()), "Selected": "Predicted Emission Reductions"}})),
                output_widget("carbonPoints"),
                full_screen = True),
            col_widths = [12, 8, 4], row_heights = [2, 7]),
        value = "carbon"),
    title = "Peatland Code Dashboard",
    id = "main",
    sidebar = ui.sidebar(
            ui.accordion(
                ui.accordion_panel("Breakdown",
                                   ui.input_radio_buttons("breakdown", None, list(BREAKDOWN_COLUMNS.keys())),
                                   ),
                ui.accordion_panel("Filters",
                                   ui.output_ui("resetFilters"),
                                   ui.accordion(
                                       *[filter_ui(column.replace(" ", "_"), column) for column in list(BREAKDOWN_COLUMNS.keys())],
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
    for column in list(BREAKDOWN_COLUMNS.keys()):
        filters[column] = filter_server(column.replace(" ", "_"), column, filters, input.resetFilters)
    
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
         
    #%%% VALUE BOXES
    
    for page in ["overview", "projects", "area", "carbon"]:
        valueBoxes_server("valueBoxes_" + page, data)
        
    #%%% LINKS
        
    @reactive.effect
    @reactive.event(input.link_projects)
    def linkProjects():
        ui.update_navs("main", "projects")
        
    @reactive.effect
    @reactive.event(input.link_area)
    def linkArea():
        ui.update_navs("main", "area")
            
    @reactive.effect
    @reactive.event(input.link_carbon)
    def linkCarbon():
        ui.update_navs("main", "carbon")
                
    #%%% PROJECTS
    
    #%%%% TABLE
    
    @render.data_frame
    def projectList():
        return render.DataTable(DISPLAY_DATA[["Name", "Country", "PIU Issuance", "Developer", "Validator", ]], width = "100%", height = "100%", summary = False)
    
    #ADD CONTROL TO ADD REMOVE/COLUMNS
    
    #%%%% MAP
        
    #%%% AREA
    
    #%%%% BREAKDOWN
    
    infoCardHeader_server("areaBreakdown_header", input.breakdown)
        
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
                    hovertemplate = "<b>" + str(row["Area Type"]) + "</b><br><i>" + str(row["Subarea Type"]) + "</i><br>%{x:.3s} ha<extra></extra>",
                    hoverlabel = {"bgcolor": "white"}
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
    
    #%%%% DISTRIBUTION
    
    areaDistribution_header = infoCardHeader_server("areaDistribution_header", input.breakdown, {"Y-axis": "PLURAL"})
    
    @render_widget
    def areaDistribution():
        df = data().copy()
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), areaDistribution_header["Y-axis"]())
        return go.Figure(
            data = [
                go.Violin(
                    x = df.loc[df[input.breakdown()] == value, input.breakdown()],
                    y = df.loc[df[input.breakdown()] == value, areaDistribution_header["Y-axis"]()],
                    spanmode = "hard",
                    points = "all",
                    pointpos = 0,
                    jitter = 0,
                    line_color = COLOUR_PALETTE[input.breakdown()][value],
                    hoveron = "points",
                    hovertext = df.loc[df[input.breakdown()] == value, "Name"],
                    hovertemplate = "<i>%{hovertext}</i><br>%{y:." + CONTINUOUS_COLUMNS[areaDistribution_header["Y-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[areaDistribution_header["Y-axis"]()]["UNIT"] + "<extra></extra>",
                    hoverlabel = {"bgcolor": "white"}
                    )
                for value in order],
            layout = go.Layout(
                xaxis = {"title_text": input.breakdown()},
                yaxis = {"title_text": areaDistribution_header["Y-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[areaDistribution_header["Y-axis"]()]["UNIT"] + ")"},
                showlegend = False,
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
    
    #%%% CARBON
    
    #%%%% PATHWAY
    
    carbonPathway_header = infoCardHeader_server("carbonPathway_header", input.breakdown, {"Y-axis": "SINGULAR"})
        
    @render_widget
    def carbonPathway():
        df = data().copy()
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), carbonPathway_header["Y-axis"]())
        df["Year"] = [list(range(df["Start Year"].min() - 1, df["End Year"].max() + 2)) for i in range(0, len(df))]
        df = df.explode("Year")
        df[carbonPathway_header["Y-axis"]()] = (df[carbonPathway_header["Y-axis"]()] / df["Duration"]).where((df["Year"] >= df["Start Year"]) & (df["Year"] <= df["End Year"]), 0)
        df = df.groupby(["Year", input.breakdown()], observed = True)[carbonPathway_header["Y-axis"]()].sum().reset_index().sort_values("Year")
        df[carbonPathway_header["Y-axis"]()] = df.groupby(input.breakdown(), observed = True)[carbonPathway_header["Y-axis"]()].cumsum()
        return go.Figure(
            data = [
                go.Scatter(
                    x = df.loc[df[input.breakdown()] == value, "Year"],
                    y = df.loc[df[input.breakdown()] == value, carbonPathway_header["Y-axis"]()],
                    stackgroup = "default",
                    name = value,
                    mode = "lines",
                    marker = {"color": COLOUR_PALETTE[input.breakdown()][value]},
                    hovertemplate = "%{y:." + CONTINUOUS_COLUMNS[carbonPathway_header["Y-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[carbonPathway_header["Y-axis"]()]["UNIT"]
                    )
                for value in order],
            layout = go.Layout(
                xaxis = {"title_text": "Year"},
                yaxis = {"title_text": carbonPathway_header["Y-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[carbonPathway_header["Y-axis"]()]["UNIT"] + ")"},
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
    
    #%%%% POINTS
    
    carbonPoints_header = infoCardHeader_server("carbonPoints_header", input.breakdown, {"X-axis": "PLURAL", "Y-axis": "PLURAL"})
    
    @render_widget
    def carbonPoints():
        df = data().copy()
        df["Original Breakdown"] = df[input.breakdown()]
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), carbonPoints_header["Y-axis"]())
        return go.Figure(
            data = [
                go.Scatter(
                    x = df.loc[df[input.breakdown()] == value, carbonPoints_header["X-axis"]()],
                    y = df.loc[df[input.breakdown()] == value, carbonPoints_header["Y-axis"]()],
                    name = value,
                    mode = "markers",
                    marker = {"color": COLOUR_PALETTE[input.breakdown()][value]},
                    customdata = df.loc[df[input.breakdown()] == value][["Original Breakdown", "Name"]],
                    hovertemplate = "<b>%{customdata[0]}</b><br><i>%{customdata[1]}</i><br>%{x:." + CONTINUOUS_COLUMNS[carbonPoints_header["X-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[carbonPoints_header["X-axis"]()]["UNIT"] + "<br>%{y:." + CONTINUOUS_COLUMNS[carbonPoints_header["Y-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[carbonPoints_header["Y-axis"]()]["UNIT"] + "<extra></extra>",
                    hoverlabel = {"bgcolor": "white"}
                    )
                for value in order],
            layout = go.Layout(
                xaxis = {"title_text": carbonPoints_header["X-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[carbonPoints_header["X-axis"]()]["UNIT"] + ")"},
                yaxis = {"title_text": carbonPoints_header["Y-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[carbonPoints_header["Y-axis"]()]["UNIT"] + ")"},
                legend = {"title_text": input.breakdown(),
                          "orientation": "h",
                          "yref": "container"},
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
    
#%% APP

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)

#TODO

#FIX DOUBLE REFRESH WHEN FILTERS USED

#ADD INFO BUTTON TO BREAKDOWN AND FILTER ACCORDIONS IN SIDEBAR; HIDE/DISABLE BREAKDOWN ON OVERVIEW PAGE

#ADDRESS COLOUR CLASHES WITH DEVELOPERS: SORT BY PROJECT COUNT WHEN ASSIGNING COLOURS

#SEPARATE MAP AND TABLE AND MAKE TABLE 8 WIDTH AND MAP 4 WIDTH: ENSURE MAP HAS BREAKDOWN

#REMOVE PROJECT COUNT CHART BUT ADD COUNT TO FILTER (E.G. Scotland (199))

#FULLY PHASE OUT INFO CARD HEADER

#ADD CO-ORDINATES AT SITES WHERE THIS IS MISSING
