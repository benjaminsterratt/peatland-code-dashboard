from shiny import run_app, App, reactive, ui

userInterface = ui.page_fillable()

def server(input):
    pass

app = App(userInterface, server)

run_app(app)