from fasthtml.common import *

app, rt = fast_app()

@app.route("/")
def startPage():
    return Div(P(f"Jagtskydningsapp"), Button("Opret ny skydning", hx_get="/nySkydning"), id="startPage")

@app.route("/nySkydning")
def nySkydning():
    return Div(P("Ny skydning oprettet! Klik for at komme tilbage til start"),hx_get="/", hx_target="#startPage", id="nySkydningPage")

if __name__ == "__main__":
    serve()