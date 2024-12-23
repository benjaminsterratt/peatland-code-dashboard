import pathlib
import re

import pandas as pd

from shiny import module, ui, reactive, render, App
from shinywidgets import output_widget, render_plotly
from faicons import icon_svg

import plotly.colors as co
import plotly.graph_objects as go

#%% FUNCTIONS

#%%% GENERAL

def insert(list, position, input):
    return(list[:position] + [input] + list[position:])

#%%% UI

def linkedCardHeader(id, text):
    return ui.div(ui.div(text), ui.input_action_link(id, "View more"), style = "display: flex; justify-content: space-between;")

#%%% SERVER

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

def orderAndTruncateBreakdown(df, breakdown, order = None, truncate = 5):
    if order is None:
        order = df[breakdown].value_counts().index.to_list()
    else:
        order = df.groupby(breakdown)[order].sum().sort_values(ascending = False).reset_index()[breakdown].to_list()
    if len(order) > truncate:
        order = order[0:5]
        df[breakdown] = df[breakdown].where(df[breakdown].isin(order), "Other")
        order.append("Other")
    return df, order

#%% INPUTS

DATA = pd.read_csv(pathlib.Path(__file__).parent / "data.csv", keep_default_na = False)

BREAKDOWN_COLUMNS = {
    "Country": "country",
    "Project Status": "project status",
    "PIU Status": "PIU status", 
    "Developer": "developer", 
    "Validator": "validator"
    }

BREAKDOWN_CHOICES = {column: DATA[column].value_counts().index.to_list() for column in list(BREAKDOWN_COLUMNS.keys())}

BREAKDOWN_COLOUR_PALETTE = {column: {insert(DATA[column].value_counts().index.to_list(), 5, "Other")[i]: co.DEFAULT_PLOTLY_COLORS[i % len(co.DEFAULT_PLOTLY_COLORS)] for i in range(0, len(BREAKDOWN_CHOICES[column]) + 1)} for column in list(BREAKDOWN_COLUMNS.keys())}

CONTINUOUS_COLUMNS = {
    "Duration": {
        "UNIT": "years", 
        "SINGULAR": "duration", 
        "PLURAL": "durations", 
        "ROUNDING": "0f"},
    "Area": {
        "UNIT": "ha", 
        "SINGULAR": "area", 
        "PLURAL": "areas",
        "ROUNDING": "3s"
        },
    "Predicted Emission Reductions": {
        "UNIT": "tCO₂e", 
        "SINGULAR": "predicted emission reductions", 
        "PLURAL": "predicted emission reductions",
        "ROUNDING": "3s"
        },
    "Predicted Claimable Emission Reductions": {
        "UNIT": "tCO₂e", 
        "SINGULAR": "predicted claimable emission reductions", 
        "PLURAL": "predicted claimable emission reductions",
        "ROUNDING": "3s"
        }
    }

AREA_COLOUR_PALETTE = {
    "Blanket Bog": {
        "": "rgba(31, 119, 180, 0.25)",
        "Near Natural": "rgba(31, 119, 180, 0.25)",
        "Modified": "rgba(31, 119, 180, 0.5)",
        "Drained (Hagg/Gully)": "rgba(31, 119, 180, 0.75)",
        "Drained (Artificial)": "rgba(31, 119, 180, 0.75)",
        "Actively Eroding (Flat Bare)": "rgba(31, 119, 180, 1)",
        "Actively Eroding (Hagg/Gully)": "rgba(31, 119, 180, 1)"
        },
    "Raised Bog": {
        "": "rgba(255, 127, 14, 0.25)",
        "Near Natural": "rgba(255, 127, 14, 0.25)",
        "Modified": "rgba(255, 127, 14, 0.5)",
        "Drained (Hagg/Gully)": "rgba(255, 127, 14, 0.75)",
        "Drained (Artificial)": "rgba(255, 127, 14, 0.75)",
        "Actively Eroding (Flat Bare)": "rgba(255, 127, 14, 1)",
        "Actively Eroding (Hagg/Gully)": "rgba(255, 127, 14, 1)"
        },
    "Fen": {
        "": "rgba(44, 160, 44, 0.25)",
        "Modified": "rgba(44, 160, 44, 0.5)",
        "Grassland (Extensive)": "rgba(44, 160, 44, 0.75)",
        "Grassland (Intensive)": "rgba(44, 160, 44, 0.75)",
        "Cropland": "rgba(44, 160, 44, 1)"
        }
    }

#%% MODULES

#%%% FILTER

@module.ui
def filter_ui(title):
    elements = [
        ui.input_checkbox_group(
            "filter", 
            None, 
            BREAKDOWN_CHOICES[title],
            selected = BREAKDOWN_CHOICES[title]
            )
        ]
    if len(BREAKDOWN_CHOICES[title]) > 5:
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
    
    selection = reactive.value(BREAKDOWN_CHOICES[name])
        
    @reactive.effect
    @reactive.event(input.filter)
    def updateSelection():
        if sorted(input.filter()) != selection():
            selection.set(sorted(input.filter()))
        
    @reactive.effect
    def updateLabels():
        df = DATA.copy()
        for column in filters:
            if column != name:
                df = df[df[column].isin(filters[column]())]
        df = pd.merge(DATA.copy()[[name]].drop_duplicates(), df[name].value_counts().reset_index().rename(columns = {"index": name, "count": "Count"}), how = "left").sort_values(["Count", name], ascending = [False, True])
        df["Count"] = df["Count"].fillna(0).astype(int)
        with reactive.isolate():
            ui.update_checkbox_group("filter", choices = {row[name]: row[name] + " (" + str(row["Count"]) + ")" for i, row in df.iterrows()}, selected = selection())
    
    if len(BREAKDOWN_CHOICES[name]) > 5:
    
        @reactive.effect
        @reactive.event(input.selectAll)
        def selectAll():
            ui.update_checkbox_group("filter", selected = BREAKDOWN_CHOICES[name])
            
        @reactive.effect
        @reactive.event(input.deselectAll)
        def deselectAll():
            ui.update_checkbox_group("filter", selected = [])
            
    if resetInput is not None:
        
        @reactive.effect
        @reactive.event(resetInput)
        def reset():
            ui.update_checkbox_group("filter", selected = BREAKDOWN_CHOICES[name])
            
    return selection

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

def buildInput(id, label, choices, selected):
    if isinstance(selected, list):
        return ui.input_checkbox_group(id, label, choices, selected = selected)
    else:
        return ui.input_radio_buttons(id, label, choices, selected = selected)

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
        buttons = ui.div(buttons, ui.popover(icon_svg("gear", height = "14.4px", margin_right = "0px"), ui.div(*[buildInput(re.sub("[^\\w]", "_", variable), ui.tags.b(variable), variables[variable]["Choices"], variables[variable]["Selected"]) for variable in variables])))
    
    return ui.div(ui.div(text), buttons, style = "display: flex; justify-content: space-between;")

@module.server
def infoCardHeader_server(input, output, session, breakdownInput = None, variables = None):
    
    if breakdownInput is not None:
        @render.text
        def breakdown():
            return BREAKDOWN_COLUMNS[breakdownInput()]
    
    if variables is not None:
        for variable in variables:
            if variables[variable] is not None:
                render.text(buildFunction(input, variable, variables[variable]))
        return {variable: getattr(input, re.sub("[^\\w]", "_", variable)) for variable in variables}

#%% UI

userInterface = ui.page_navbar(
    ui.nav_spacer(),
    ui.nav_panel(
        "Overview",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_overview"),
            ui.card(
                ui.card_header(linkedCardHeader("link_projects", "Projects")),
                output_widget("overviewProjects")
                ),
            ui.card(
                ui.card_header(linkedCardHeader("link_area", "Area")),
                output_widget("overviewArea")
                ),
            ui.card(
                ui.card_header(linkedCardHeader("link_carbon", "Carbon")),
                output_widget("overviewCarbon")
                ),
            col_widths = [12, 4, 4, 4], row_heights = [2, 7]),
        value = "overview"),
    ui.nav_panel(
        "Projects",
        ui.layout_columns(
            valueBoxes_ui("valueBoxes_projects", 1),
            ui.card(
                ui.card_header(infoCardHeader_ui("projectsTable_header", "Table", "Table of projects.", {"Columns": {"Choices": ["Start Year", "End Year"] + list(CONTINUOUS_COLUMNS.keys()), "Selected": ["Duration", "Area", "Predicted Emission Reductions"]}})),
                ui.output_data_frame("projectsTable"),
                full_screen = True),
            ui.card(
                ui.card_header(infoCardHeader_ui("projectsMap_header", "Map", "Map of projects broken down by {breakdown}.")),
                output_widget("projectsMap"),
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
                ui.card_header(infoCardHeader_ui("carbonPathway_header", "Pathway", "Cumulative {Y-axis} across projects' durations broken down by {breakdown}. Projects without start dates assumed to start in 2025.", {"Y-axis": {"Choices": ["Predicted Emission Reductions", "Predicted Claimable Emission Reductions"], "Selected": "Predicted Emission Reductions"}})),
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
                id = "sidebar", open = ["Filters"]),
            width = 420),
    fillable = True,
    header = ui.head_content(ui.include_css(pathlib.Path(__file__).parent / "app.css"))
    )

#%% SERVER

def server(input, output, session):

    #%%% SIDEBAR    

    filters = {}
    for column in list(BREAKDOWN_COLUMNS.keys()):
        filters[column] = filter_server(column.replace(" ", "_"), column, filters, input.resetFilters)
    
    enableResetFilter = reactive.value(False)
    
    data = reactive.value(DATA)
    
    @reactive.effect
    def updateData():
        df = DATA.copy()
        filtered = False
        for column in filters:
            selected = filters[column]()
            if len(selected) != len(BREAKDOWN_CHOICES[column]):
                filtered = True
                df = df[df[column].isin(selected)]
        if set(df["ID"]) != set(data()["ID"]):    
            enableResetFilter.set(filtered)
            data.set(df)
    
    @render.ui
    def resetFilters():
        if enableResetFilter.get():
            return ui.input_action_button("resetFilters", "Reset filters", style = "margin-bottom: 16px;")
        else:
            return ui.input_action_button("resetFilters", "Reset filters", style = "margin-bottom: 16px;", disabled = True)
         
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
        
    #%%% OVERVIEW
    
    #%%%% PROJECTS
    
    @render_plotly
    def overviewProjects():
        return go.Figure(
            data = [
                go.Scattermap(
                    mode = "markers",
                    hovertemplate = "%{hovertext}<extra></extra>",
                    hoverlabel = {"bgcolor": "white"}
                    )
                ],
            layout = go.Layout(
                map = {
                    "center": {"lat": 56, "lon": -2.5},
                    "zoom": 4
                    },
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select", "lasso"]},
                template = "plotly_white"
                )
            )
    
    @reactive.calc
    def overviewProjectsUpdate():
        df = data().copy()
        df = df[(df["Latitude"] != "") & (df["Longitude"] != "")]
        overviewProjects.widget.update_traces(
            lat = df["Latitude"],
            lon = df["Longitude"],
            hovertext = df["Name"]
            )
    
    #%%%% AREA
    
    @render_plotly
    def overviewArea():
        return go.Figure(
            layout = go.Layout(
                margin = {"l": 0, "r": 0, "t": 28, "b": 28},
                template = "plotly_white"
                )
            )
        
    @reactive.calc
    def overviewAreaUpdate():
        values = data().copy().sum().to_dict()
        df = pd.concat([pd.DataFrame({"Type": [re.sub(".*; (.*); .*", "\\1", key)], "Sub-type": [re.sub(".*; .*; (.*)", "\\1", key)], "Area": [values[key]]}) for key in values if "Subarea" in key])
        df = df.loc[df["Area"] > 0]
        df_type = df.groupby("Type")["Area"].sum().reset_index()
        overviewArea.widget.data = []
        overviewArea.widget.add_treemap(
            ids = ["Peatland"] + df_type["Type"].tolist() + (df["Type"] + df["Sub-type"]).tolist(),
            labels = ["Peatland"] + df_type["Type"].tolist() + df["Sub-type"].tolist(),
            parents = [""] + ["Peatland"] * len(df_type) + df["Type"].tolist(),
            values = [df_type["Area"].sum()] + df_type["Area"].tolist() + df["Area"].tolist(),
            branchvalues = "total",
            marker_colors = ["white"] + [AREA_COLOUR_PALETTE[i][""] for i in df_type["Type"].tolist()] + [AREA_COLOUR_PALETTE[row["Type"]][row["Sub-type"]] for i, row in df.iterrows()],
            hovertemplate = "<i>%{label}</i><br>%{value:.3s} ha<extra></extra>",
            hoverlabel = {"bgcolor": "white"}
            )
    
    #%%%% CARBON
    
    @render_plotly
    def overviewCarbon():
        return go.Figure(
            layout = go.Layout(
                xaxis = {"title_text": "Year"},
                yaxis = {"title_text": "Predicted emission reductions (" + CONTINUOUS_COLUMNS["Predicted Emission Reductions"]["UNIT"] + ")"},
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": "autoScale2d"},
                template = "plotly_white"
                )
            )
    
    @reactive.calc
    def overviewCarbonUpdate():
        df = data().copy()
        df["Year"] = [list(range(df["Start Year"].min() - 1, df["End Year"].max() + 2)) for i in range(0, len(df))]
        df = df.explode("Year")
        df["Predicted Emission Reductions"] = (df["Predicted Emission Reductions"] / df["Duration"]).where((df["Year"] >= df["Start Year"]) & (df["Year"] <= df["End Year"]), 0)
        df = df.groupby("Year")["Predicted Emission Reductions"].sum().reset_index().sort_values("Year")
        df["Predicted Emission Reductions"] = df["Predicted Emission Reductions"].cumsum()
        overviewCarbon.widget.data = []
        overviewCarbon.widget.add_trace(
            go.Scatter(
                x = df["Year"],
                y = df["Predicted Emission Reductions"],
                stackgroup = "default",
                name = "Predicted emission reductions",
                mode = "lines",
                hovertemplate = "%{x:.0f}<br>%{y:." + CONTINUOUS_COLUMNS["Predicted Emission Reductions"]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS["Predicted Emission Reductions"]["UNIT"] + "<extra></extra>",
                hoverlabel = {"bgcolor": "white"}
                )
            )
                
    #%%% PROJECTS
    
    #%%%% MODAL
    
    modal = reactive.value(None)
    modal_locationData = reactive.value(None)
    modal_areaData = reactive.value(None)
    
    @reactive.effect
    def projectsModal():
        if modal() is not None:
            values = DATA.copy().loc[DATA["Name"] == modal()].reset_index().to_dict("index")[0]
            paragraph1 = [ui.tags.b(values["Name"]), " is a peatland restoration project in ", values["Country"], " with ", ui.tags.b(values["Developer"]), " as the project developer. "]
            if values["Project Status"] == "Under Development":
                paragraph1 = paragraph1 + ["The project is under development and the project plan has not yet been validated "]
                if values["Validator"] == "N/A":
                    paragraph1 = paragraph1 + ["or a validator selected."]
                else:
                    paragraph1 = paragraph1 + ["but ", ui.tags.b(values["Validator"]), " has been selected as the validator."]
            elif values["Project Status"] == "Validated":
                paragraph1 = paragraph1 + ["The project plan has been validated by ", ui.tags.b(values["Validator"]), " "]
                if values["PIU Status"] == "Unissued":
                    paragraph1 = paragraph1 + ["but restoration is still to be validated and PIUs are not yet issued."]
                elif values["PIU Status"] == "Issued":
                    paragraph1 = paragraph1 + ["and PIUs have been issued ahead of restoration validation which is still to occur."]
                else:
                    raise ValueError("Unexpected 'PIU Status' value.")
            elif values["Project Status"] == "Restoration Validated":
                paragraph1 = paragraph1 + ["Restoration has been completed and validated by ", ui.tags.b(values["Validator"]), " "]
                if values["PIU Status"] == "Unissued":
                    paragraph1 = paragraph1 + [" but PIUs are yet to be issued."]
                elif values["PIU Status"] == "Issued":
                    paragraph1 = paragraph1 + [" and PIUs have been issued."]
                else:
                    raise ValueError("Unexpected 'PIU Status' value.")
            else:
                raise ValueError("Unexpected 'Project Status' value.")
            paragraph2 = ["The project covers ", formatNumber(values["Area"]), " ha and is predicted to lead to ", formatNumber(values["Predicted Emission Reductions"]), " tCO₂e of emission reductions over ", values["Duration"], " years"]
            if values["Start Year"] == 2025:
                paragraph2 = paragraph2 + ["."]
            else:
                paragraph2 = paragraph2 + [", starting in ", values["Start Year"], "."]
            if values["Predicted Emission Reductions"] != 0:
                paragraph2 = paragraph2 + [" ", formatNumber(values["Predicted Claimable Emission Reductions"]) , " tCO₂e of this (", round(values["Predicted Claimable Emission Reductions"] / values["Predicted Emission Reductions"] * 100), "%) is claimable."]
            df_subtype = pd.concat([pd.DataFrame({"Type": [re.sub(".*; (.*); .*", "\\1", key)], "Sub-type": [re.sub(".*; .*; (.*)", "\\1", key)], "Area": [values[key]]}) for key in values if "Subarea" in key])
            modal_areaData.set({"df": df_subtype, "name": values["Name"]})
            df_subtype["Area Percentage"] = df_subtype["Area"] / df_subtype["Area"].sum() * 100
            df_type = df_subtype.loc[df_subtype["Area Percentage"] > 0].groupby("Type")["Area Percentage"].sum().reset_index().sort_values("Area Percentage", ascending = False)
            df_subtype = df_subtype.loc[(df_subtype["Type"] == df_type["Type"].iloc[0]) & (df_subtype["Area Percentage"] >= 10)].sort_values("Area Percentage", ascending = False)
            paragraph3 = "The site is "
            if len(df_type) == 1:
                paragraph3 = paragraph3 + "fully "
            elif round(df_type["Area Percentage"].iloc[0]) == 100:
                paragraph3 = paragraph3 + "almost fully "
            else:
                paragraph3 = paragraph3 + str(round(df_type["Area Percentage"].iloc[0])) + "% "
            paragraph3 = paragraph3 + df_type["Type"].iloc[0].lower()
            if len(df_subtype) > 0:
                paragraph3 = paragraph3 + ", "
                if (len(df_subtype) == 1) & (df_subtype["Area Percentage"].iloc[0] == df_type["Area Percentage"].iloc[0]):
                    paragraph3 = paragraph3 + " all of which is classed as '" + df_subtype["Sub-type"].iloc[0] + "'."
                else:
                    paragraph3 = paragraph3 + "including "
                    if len(df_subtype) > 1:
                        for i in range(0, len(df_subtype) - 1):
                            paragraph3 = paragraph3 + formatNumber(df_subtype["Area"].iloc[i]) + " ha classed as '" + df_subtype["Sub-type"].iloc[i] + "', "
                        paragraph3 = paragraph3 + " and "
                    paragraph3 = paragraph3 + formatNumber(df_subtype["Area"].iloc[-1]) + " ha classed as '" + df_subtype["Sub-type"].iloc[-1] + "'."
            else:
                paragraph3 = paragraph3 + "."
            arguments = [
                ui.p(paragraph1),
                ui.p(paragraph2),
                ui.accordion(ui.accordion_panel("Area Types", output_widget("projectsModalArea")), {"style": "margin-bottom: 16px"}),
                paragraph3
                ]
            if values["Latitude"] != "" and values["Longitude"] != "":
                arguments = insert(arguments, 1, ui.accordion(ui.accordion_panel("Location", output_widget("projectsModalLocation")), {"style": "margin-bottom: 16px"}))
                modal_locationData.set({"latitude": values["Latitude"], "longitude": values["Longitude"], "name": values["Name"]})
            ui.modal_show(
                ui.modal(
                    *arguments,
                    title = modal(), 
                    footer = [
                        ui.input_action_button("projectsModalClose", "Close", icon = icon_svg("xmark", height = "14.4px"), style = "flex: 1 0 auto;"), 
                        ui.a(icon_svg("arrow-up-right-from-square", height = "14.4px"), " View on Peatland Code Registry ", href = values["URL"], style = "flex: 1 0 auto;", class_ = "btn btn-default")
                        ],
                    size = "m")
                )
    
    @render_plotly
    def projectsModalLocation():
        if modal_locationData() is not None:
            return go.Figure(
                data = [
                    go.Scattermap(
                        lat = [modal_locationData()["latitude"]],
                        lon = [modal_locationData()["longitude"]],
                        mode = "markers",
                        hovertext = [modal_locationData()["name"]],
                        hovertemplate = "%{hovertext}<extra></extra>",
                        hoverlabel = {"bgcolor": "white"}
                        )
                    ],
                layout = go.Layout(
                    map = {
                        "center": {"lat": float(modal_locationData()["latitude"]), "lon": float(modal_locationData()["longitude"])},
                        "zoom": 5
                        },
                    margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                    modebar = {"remove": ["select", "lasso"]},
                    template = "plotly_white"
                    )
                )
            
    @render_plotly
    def projectsModalArea():
        return go.Figure(
            layout = go.Layout(
                margin = {"l": 0, "r": 0, "t": 28, "b": 28},
                template = "plotly_white"
                )
            )
    
    @reactive.effect
    def projectsModalAreaUpdate():
        if modal_areaData() is not None:
            df = modal_areaData()["df"].copy()
            df = df.loc[df["Area"] > 0]
            df_type = df.groupby("Type")["Area"].sum().reset_index()
            projectsModalArea.widget.data = []
            projectsModalArea.widget.add_treemap(
                ids = [modal_areaData()["name"]] + df_type["Type"].tolist() + (df["Type"] + df["Sub-type"]).tolist(),
                labels = [modal_areaData()["name"]] + df_type["Type"].tolist() + df["Sub-type"].tolist(),
                parents = [""] + [modal_areaData()["name"]] * len(df_type) + df["Type"].tolist(),
                values = [df_type["Area"].sum()] + df_type["Area"].tolist() + df["Area"].tolist(),
                branchvalues = "total",
                marker_colors = ["white"] + [AREA_COLOUR_PALETTE[i][""] for i in df_type["Type"].tolist()] + [AREA_COLOUR_PALETTE[row["Type"]][row["Sub-type"]] for i, row in df.iterrows()],
                hovertemplate = "<i>%{label}</i><br>%{value:.3r} ha<extra></extra>",
                hoverlabel = {"bgcolor": "white"}
                )
        
    @reactive.effect
    @reactive.event(input.projectsModalClose)
    def projectsModalClose():
        modal.set(None)
        ui.modal_remove()
            
    #%%%% TABLE
    
    projectsTable_header = infoCardHeader_server("projectsTable_header", variables = {"Columns": None})
    
    @render.data_frame
    def projectsTable():
        df = data().copy()
        if "Start Year" or "End Year" in projectsTable_header["Columns"]():
            df["Start Year"] = df["Start Year"].where(df["Start Year"] != 2025, None)
        if "End Year" in projectsTable_header["Columns"]():
            df["End Year"] = df["End Year"].where(~df["Start Year"].isna(), None)
        df = df[["Name", input.breakdown(), *projectsTable_header["Columns"]()]].rename(columns = {column: column + " (" + CONTINUOUS_COLUMNS[column]["UNIT"] + ")" for column in projectsTable_header["Columns"]() if column in CONTINUOUS_COLUMNS})
        return render.DataTable(df, width = "100%", height = "100%", summary = False, selection_mode = "row")
    
    @reactive.effect
    @reactive.event(projectsTable.cell_selection)
    async def projectsTableTriggerModal():
        if len(projectsTable.cell_selection()["rows"]) == 1:
            modal.set(data()["Name"].iloc[projectsTable.cell_selection()["rows"][0]])
            await projectsTable.update_cell_selection(None)
        
    #%%%% MAP
    
    infoCardHeader_server("projectsMap_header", input.breakdown)
    
    @render_plotly
    def projectsMap():
        return go.Figure(
            data = [go.Scattermap()],
            layout = go.Layout(
                map = {
                    "center": {"lat": 56, "lon": -2.5},
                    "zoom": 4
                    },
                legend = {"orientation": "h",
                          "yref": "container"},
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select", "lasso"]},
                template = "plotly_white"
                )
            )
    
    def projectsMapTriggerModal(trace, points, selector):
        if len(points.point_inds) == 1:
            modal.set(trace.hovertext[points.point_inds[0]])
        
    @reactive.calc
    def projectsMapUpdate():
        df = data().copy()
        df = df[(df["Latitude"] != "") & (df["Longitude"] != "")]
        df, order = orderAndTruncateBreakdown(df, input.breakdown())
        projectsMap.widget.data = [projectsMap.widget.data[0]]
        projectsMap.widget.add_traces([
            go.Scattermap(
                lat = df.loc[df[input.breakdown()] == value, "Latitude"],
                lon = df.loc[df[input.breakdown()] == value, "Longitude"],
                name = value,
                mode = "markers",
                marker = {"color": BREAKDOWN_COLOUR_PALETTE[input.breakdown()][value]},
                hovertext = df.loc[df[input.breakdown()] == value, "Name"],
                hovertemplate = "%{hovertext}<extra></extra>",
                hoverlabel = {"bgcolor": "white"}
                )
            for value in order])
        for i in range(1, len(projectsMap.widget.data)):
            projectsMap.widget.data[i].on_click(projectsMapTriggerModal)

    #%%% AREA
    
    #%%%% BREAKDOWN
    
    infoCardHeader_server("areaBreakdown_header", input.breakdown)
    
    @render_plotly
    def areaBreakdown():
        return go.Figure(
            layout = go.Layout(
                xaxis = {"title_text": "Area (ha)"},
                barmode = "stack",
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
            
    @reactive.calc
    def areaBreakdownUpdate():
        df = data().copy()
        df = df.melt(input.breakdown(), [column for column in df.columns if column.startswith("Subarea")], "Subarea Type", "Subarea Area")
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), "Subarea Area")
        df[input.breakdown()] = df[input.breakdown()].astype(pd.CategoricalDtype(order, ordered = True))
        df["Area Type"] = df["Subarea Type"].str.replace(".*; (.*);.*", "\\1", regex = True)
        df["Area Type"] = df["Area Type"].astype(pd.CategoricalDtype(df.groupby("Area Type")["Subarea Area"].sum().reset_index().sort_values("Subarea Area")["Area Type"].to_list(), ordered = True))
        df["Subarea Type"] = df["Subarea Type"].str.replace(".*; ", "", regex = True).astype(pd.CategoricalDtype(["Near Natural", "Modified", "Drained (Artificial)", "Drained (Hagg/Gully)", "Grassland (Extensive)", 'Grassland (Intensive)', "Actively Eroding (Flat Bare)", "Actively Eroding (Hagg/Gully)", "Cropland"], ordered = True))
        df = df.groupby([input.breakdown(), "Area Type", "Subarea Type"], observed = True)["Subarea Area"].sum().reset_index().sort_values(input.breakdown())
        areaBreakdown.widget.data = []
        areaBreakdown.widget.add_traces([
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
            for i, row in df[["Area Type", "Subarea Type"]].drop_duplicates().sort_values(["Area Type", "Subarea Type"], ascending = False).iterrows()])
        areaBreakdown.widget.update_layout(
            yaxis_title_text = input.breakdown()
            )
    
    #%%%% DISTRIBUTION
    
    areaDistribution_header = infoCardHeader_server("areaDistribution_header", input.breakdown, {"Y-axis": "PLURAL"})
    
    @render_plotly
    def areaDistribution():
        return go.Figure(
            layout = go.Layout(
                showlegend = False,
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
        
    @reactive.calc
    def areaDistributionUpdate():
        df = data().copy()
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), areaDistribution_header["Y-axis"]())
        areaDistribution.widget.data = []
        areaDistribution.widget.add_traces([
            go.Violin(
                x = df.loc[df[input.breakdown()] == value, input.breakdown()],
                y = df.loc[df[input.breakdown()] == value, areaDistribution_header["Y-axis"]()],
                spanmode = "hard",
                points = "all",
                pointpos = 0,
                jitter = 0,
                line_color = BREAKDOWN_COLOUR_PALETTE[input.breakdown()][value],
                hoveron = "points",
                hovertext = df.loc[df[input.breakdown()] == value, "Name"],
                hovertemplate = "<i>%{hovertext}</i><br>%{y:." + CONTINUOUS_COLUMNS[areaDistribution_header["Y-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[areaDistribution_header["Y-axis"]()]["UNIT"] + "<extra></extra>",
                hoverlabel = {"bgcolor": "white"}
                )
            for value in order])
        areaDistribution.widget.update_layout(
            xaxis_title_text = input.breakdown(),
            yaxis_title_text = areaDistribution_header["Y-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[areaDistribution_header["Y-axis"]()]["UNIT"] + ")"
            )
    
    #%%% CARBON
    
    #%%%% PATHWAY
    
    carbonPathway_header = infoCardHeader_server("carbonPathway_header", input.breakdown, {"Y-axis": "SINGULAR"})
        
    @render_plotly
    def carbonPathway():
        return go.Figure(
            layout = go.Layout(
                xaxis = {"title_text": "Year"},
                legend = {"traceorder": "normal",
                          "orientation": "h",
                          "yref": "container"},
                hovermode = "x unified",
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": "autoScale2d"},
                template = "plotly_white"
                )
            )
    
    @reactive.calc
    def carbonPathwayUpdate():
        df = data().copy()
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), carbonPathway_header["Y-axis"]())
        df["Year"] = [list(range(df["Start Year"].min() - 1, df["End Year"].max() + 2)) for i in range(0, len(df))]
        df = df.explode("Year")
        df[carbonPathway_header["Y-axis"]()] = (df[carbonPathway_header["Y-axis"]()] / df["Duration"]).where((df["Year"] >= df["Start Year"]) & (df["Year"] <= df["End Year"]), 0)
        df = df.groupby(["Year", input.breakdown()])[carbonPathway_header["Y-axis"]()].sum().reset_index().sort_values("Year")
        df[carbonPathway_header["Y-axis"]()] = df.groupby(input.breakdown())[carbonPathway_header["Y-axis"]()].cumsum()
        carbonPathway.widget.data = []
        carbonPathway.widget.add_traces([
            go.Scatter(
                x = df.loc[df[input.breakdown()] == value, "Year"],
                y = df.loc[df[input.breakdown()] == value, carbonPathway_header["Y-axis"]()],
                stackgroup = "default",
                name = value,
                mode = "lines",
                marker = {"color": BREAKDOWN_COLOUR_PALETTE[input.breakdown()][value]},
                hovertemplate = "%{y:." + CONTINUOUS_COLUMNS[carbonPathway_header["Y-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[carbonPathway_header["Y-axis"]()]["UNIT"]
                )
            for value in order])
        carbonPathway.widget.update_layout(
            yaxis_title_text = carbonPathway_header["Y-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[carbonPathway_header["Y-axis"]()]["UNIT"] + ")",
            legend_title_text = input.breakdown()
            )
    
    #%%%% POINTS
    
    carbonPoints_header = infoCardHeader_server("carbonPoints_header", input.breakdown, {"X-axis": "PLURAL", "Y-axis": "PLURAL"})
    
    @render_plotly
    def carbonPoints():
        return go.Figure(
            layout = go.Layout(
                legend = {"orientation": "h",
                          "yref": "container"},
                margin = {"l": 0, "r": 0, "t": 28, "b": 0},
                modebar = {"remove": ["select2d", "lasso2d", "autoScale2d"]},
                template = "plotly_white"
                )
            )
    
    @reactive.calc
    def carbonPointsUpdate():
        df = data().copy()
        df["Original Breakdown"] = df[input.breakdown()]
        df, order = orderAndTruncateBreakdown(df, input.breakdown(), carbonPoints_header["Y-axis"]())
        carbonPoints.widget.data = []
        carbonPoints.widget.add_traces([
            go.Scatter(
                x = df.loc[df[input.breakdown()] == value, carbonPoints_header["X-axis"]()],
                y = df.loc[df[input.breakdown()] == value, carbonPoints_header["Y-axis"]()],
                name = value,
                mode = "markers",
                marker = {"color": BREAKDOWN_COLOUR_PALETTE[input.breakdown()][value]},
                hovertext = df.loc[df[input.breakdown()] == value, "Name"],
                hovertemplate = "<i>%{hovertext}</i><br>%{x:." + CONTINUOUS_COLUMNS[carbonPoints_header["X-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[carbonPoints_header["X-axis"]()]["UNIT"] + "<br>%{y:." + CONTINUOUS_COLUMNS[carbonPoints_header["Y-axis"]()]["ROUNDING"] + "} " + CONTINUOUS_COLUMNS[carbonPoints_header["Y-axis"]()]["UNIT"] + "<extra></extra>",
                hoverlabel = {"bgcolor": "white"}
                )
            for value in order])
        carbonPoints.widget.update_layout(
            xaxis_title_text = carbonPoints_header["X-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[carbonPoints_header["X-axis"]()]["UNIT"] + ")",
            yaxis_title_text = carbonPoints_header["Y-axis"]().capitalize() + " (" + CONTINUOUS_COLUMNS[carbonPoints_header["Y-axis"]()]["UNIT"] + ")",
            legend_title_text = input.breakdown()
            )
        
    #%%% UPDATES
        
    @reactive.effect(priority = -1)
    def updateTrigger():
        if input.main() == "overview":
            ui.update_accordion("sidebar", show = ["Filters"])
            overviewProjectsUpdate()
            overviewAreaUpdate()
            overviewCarbonUpdate()
        else:
            ui.update_accordion("sidebar", show = ["Breakdown", "Filters"])
            if input.main() == "projects":
                projectsMapUpdate()
            elif input.main() == "area":
                areaBreakdownUpdate()
                areaDistributionUpdate()
            elif input.main() == "carbon":
                carbonPathwayUpdate()
                carbonPointsUpdate()
            else:
                raise ValueError("input.main() not in ['overview', 'projects', 'area', 'carbon']")
    
#%% APP

app = App(userInterface, server)
