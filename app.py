from shiny import run_app, App, reactive, ui

import pandas as pd

DATA = pd.read_csv("data.csv")

userInterface = ui.page_sidebar(
    ui.sidebar(
        ui.accordion(
            ui.accordion_panel("Breakdown",
                               ui.input_radio_buttons("groupby", None, ["Type", "Country", "Developer", "Validator", "Status", "PIUs Listed"]),
                               ),
            ui.accordion_panel("Filters",
                               ui.accordion(
                                   ui.accordion_panel("Type"),
                                   ui.accordion_panel("Country"),
                                   ui.accordion_panel("Developer"),
                                   ui.accordion_panel("Validator"),
                                   ui.accordion_panel("Status"),
                                   ui.accordion_panel("PIUs Listed")
                                   )
                               )
            ),
        title = "Peatland Code Dashboard"),
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
        ui.navset_card_underline(
            ui.nav_panel("List"),
            ui.nav_panel("Map"),
            title = "Projects"
            ),
        col_widths = [8, 4]),
    fillable = True)

def server(input):
    pass

app = App(userInterface, server)

if __name__ == "__main__":
    run_app(app)
