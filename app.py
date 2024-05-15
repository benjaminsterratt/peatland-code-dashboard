from shiny import run_app, App, reactive, ui

import pandas as pd

#%% GLOBALS

DATA = pd.read_csv("data.csv", keep_default_na = False)

DATA["Country"] = DATA["Country"].astype(pd.CategoricalDtype(["England", "Scotland", "Wales", "Northern Ireland"], ordered = True))
DATA["Status"] = DATA["Status"].astype(pd.CategoricalDtype(["Under Development", "Validated", "Restoration Validated"], ordered = True))
DATA["PIUs Listed"] = DATA["PIUs Listed"].astype(pd.CategoricalDtype(["Yes", "No"], ordered = True))

GROUPING_COLUMNS = ["Type", "Country", "Developer", "Validator", "Status", "PIUs Listed"]

#%% FUNCTIONS

def ui_filter(columnName):
    choices = list(DATA[columnName].sort_values().unique())
    if len(choices) < 5:
        return ui.accordion_panel(
            columnName,
            ui.input_checkbox_group(
                "filter_" + columnName.replace(" ", "_"), 
                None, 
                choices,
                selected = choices)
            )
    else:
        return ui.accordion_panel(
            columnName,
            ui.div(
                ui.input_select(
                    "filter_" + columnName.replace(" ", "_"), 
                    None, 
                    choices,
                    selected = choices,
                    multiple = True,
                    size = round(len(choices)/2)
                    )
                )
            )

#%% UI

userInterface = ui.page_sidebar(
    ui.sidebar(
        ui.accordion(
            ui.accordion_panel("Breakdown",
                               ui.input_radio_buttons("groupby", None, GROUPING_COLUMNS),
                               ),
            ui.accordion_panel("Filters",
                               ui.accordion(
                                   *[ui_filter(column) for column in GROUPING_COLUMNS],
                                   open = False)
                               ),
            open = True),
        width = 400, title = "Peatland Code Dashboard"),
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
            title = "Projects"
            ),
        col_widths = [8, 4]),
    fillable = True)

#%% SERVER

def server(input):
    pass

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)
