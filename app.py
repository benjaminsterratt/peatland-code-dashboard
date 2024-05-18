from shiny import module, ui, reactive, App, run_app

import pandas as pd

#%% INPUTS

DATA = pd.read_csv("data.csv", keep_default_na = False)

DATA["Country"] = DATA["Country"].astype(pd.CategoricalDtype(["England", "Scotland", "Wales", "Northern Ireland"], ordered = True))
DATA["Status"] = DATA["Status"].astype(pd.CategoricalDtype(["Under Development", "Validated", "Restoration Validated"], ordered = True))
DATA["PIUs Listed"] = DATA["PIUs Listed"].astype(pd.CategoricalDtype(["Yes", "No"], ordered = True))

GROUPING_COLUMNS = ["Type", "Country", "Developer", "Validator", "Status", "PIUs Listed"]

#%% PRE-PROCESSING

CHOICES = {column: list(DATA[column].sort_values().unique()) for column in GROUPING_COLUMNS}

#%% MODULES

#%%% FILTER

@module.ui
def filter_ui(choices, controlsThreshold, title):
    elements = [
        ui.input_checkbox_group(
            "filter", 
            None, 
            choices,
            selected = choices
            )
        ]
    if len(choices) > controlsThreshold:
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
def filter_server(input, output, session, choices, controlsThreshold, resetInput = None):
    
    if len(choices) > controlsThreshold:
    
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
                               ui.input_radio_buttons("groupby", None, GROUPING_COLUMNS),
                               ),
            ui.accordion_panel("Filters",
                               ui.input_action_button("resetFilters", "Reset filters", style = "margin-left: 20px; margin-right: 20px; margin-bottom: 32px;"),
                               ui.accordion(
                                   *[filter_ui(column.replace(" ", "_"), CHOICES[column], 4, column) for column in GROUPING_COLUMNS],
                                   open = False)
                               ),
            open = True),
        width = 420, title = "Peatland Code Dashboard"),
    ui.layout_columns(
        ui.layout_columns(
            ui.card(
                ui.card_header("Carbon Pathway")
                ),
            ui.card(
                ui.card_header("Key Statistics")
                ),
            ui.card(
                ui.card_header("Area Breakdown")
                ),
            col_widths = [12, 6, 6]),
        ui.navset_card_pill(
            ui.nav_panel("List"),
            ui.nav_panel("Map"),
            title = "Projects"),
        col_widths = [8, 4]),
    fillable = True)

#%% SERVER

def server(input, output, session):

    filters = {}
    for column in GROUPING_COLUMNS:
        filters[column] = filter_server(column.replace(" ", "_"), CHOICES[column], 4, input.resetFilters)
        
    @reactive.calc
    def data():
        data = DATA.copy()
        for column in filters:
            data = data[data[column].isin(filters[column]())]
        return data

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)
