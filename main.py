import os
import pandas as pd
from dotenv import load_dotenv
from fasthtml.common import *
from fasthtml.svg import *
from supabase import create_client
from hashlib import sha256
from monsterui.all import *

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SESSION_TOKEN = "jagtskydningsapp_token"

DropDown_Sideduer_default = list(reversed(range(0, 11)))
DropDown_Skud_default = ['10', '11', '12', '13', '14']
        
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app, rt = fast_app(secret_key="superhemmeligkey", hdrs=Theme.blue.headers())

def getShootingData(userId: int = None):
    if userId is None:
        return []
    try:
        response = supabase.table("skydning").select("*").eq("userId", userId).execute()
    except Exception as e:
        print(f"Fejl ved hentning af data: {e}")
        return []
    return response.data

def getAnledninger():
    return ["Vælg anledning", "Træning", "Tavle", "DM", "Femkant", "Grand Prix", "Amtsturnering", "Hold DM", "Andet Konkurrence", "Andet"]

def deleteShootingData(skydning_id: int, userId: int = None):
    try:
        response = supabase.table("skydning").delete().eq("id", skydning_id).eq("userId", userId).execute()
    except Exception as e:
        print(f"Fejl ved sletning af data: {e}")
        return False
    return True

def getAverages(data):
    if not data:
        return {}
    df = pd.DataFrame(data)
    occasion_averages = df.groupby("occasion").agg({
        "result_hit": "mean",
        "result_shots": "mean",
        "venstre": "mean",
        "venstre_skud": "mean",
        "hoejre": "mean",
        "hoejre_skud": "mean",
        "bag": "mean",
        "bag_skud": "mean",
        "spids": "mean",
        "spids_skud": "mean"
    }).reset_index()
    location_averages = df.groupby("place").agg({
        "result_hit": "mean",
        "result_shots": "mean",
        "venstre": "mean",
        "venstre_skud": "mean",
        "hoejre": "mean",
        "hoejre_skud": "mean",
        "bag": "mean",
        "bag_skud": "mean",
        "spids": "mean",
        "spids_skud": "mean"
    }).reset_index()
    normal_averages = df.agg({
        "result_hit": "mean",
        "result_shots": "mean",
        "venstre": "mean",
        "venstre_skud": "mean",
        "hoejre": "mean",
        "hoejre_skud": "mean",
        "bag": "mean",
        "bag_skud": "mean",
        "spids": "mean",
        "spids_skud": "mean"
    }).to_frame().T
    return {
        "occasion_averages": occasion_averages.to_dict(orient="records"),
        "location_averages": location_averages.to_dict(orient="records"),
        "normal_averages": normal_averages.to_dict(orient="records")[0]
    }

def saveShootingData(place: str, useriD: int, date: str, occation: str, type: int, result_hit: int, result_shot: int, venstre :int, venstre_skud: int, hoejre: int, hoejre_skud: int, bag: int , bag_skud: int, spids: int, spids_skud: int):
    try:
        response = supabase.table("skydning").insert({
            "place": place,
            "userId": useriD,
            "date": date,
            "occasion": occation,
            "type": type,
            "result_hit": result_hit,
            "result_shots": result_shot,
            "venstre": venstre,
            "venstre_skud": venstre_skud,
            "hoejre": hoejre,
            "hoejre_skud": hoejre_skud,
            "bag": bag,
            "bag_skud": bag_skud,
            "spids": spids,
            "spids_skud": spids_skud
        }).execute()
    except Exception as e:
        print(f"Fejl ved gemning af data: {e}")
        return False
    return True

def getUserData(username: str, password: str):
    try:
        response = supabase.table("bruger").select("*").eq("username", username).eq("password", hash_password(password)).execute()
    except Exception as e:
        print(f"Fejl ved hentning af brugerdata: {e}")
        return None
    return response.data[0] if response.data else None

def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()


def tilFoejSkydniner(entry):
    return Tr(
        Td(entry["place"], style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(entry["date"], style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(entry["occasion"], style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(str(entry["type"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(str(entry["result_hit"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(str(entry["result_shots"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(str(entry["venstre"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["venstre_skud"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["hoejre"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["hoejre_skud"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["bag"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["bag_skud"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["spids"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"), 
        Td(str(entry["spids_skud"]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
        Td(A("Slet", href=f"/sletSkydning/{entry['id']}", style="display: inline-block; margin: 5px; padding: 5px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;"),
        )
    )

def build_duer_grid(sideduer, skud):

    return Div(
        Grid(
            LabelSelect(
                *Options(*[str(i) for i in sideduer], selected_idx=0),
                label="Venstreduer",
                name="skydning_venstre"
            ),
            LabelSelect(
                *Options(*[str(i) for i in sideduer], selected_idx=0),
                label="Bagduer",
                name="skydning_bag"
            ),
            LabelSelect(
                *Options(*[str(i) for i in sideduer], selected_idx=0),
                label="Højreduer",
                name="skydning_hoejre"
            ),
            LabelSelect(
                *Options(*[str(i) for i in sideduer], selected_idx=0),
                label="Spidsduer",
                name="skydning_spids"
            ),

            LabelSelect(
                *Options(*[str(i) for i in skud], selected_idx=0),
                label="Venstre skud",
                name="skydning_venstre_skud"
            ),
            LabelSelect(
                *Options(*[str(i) for i in skud], selected_idx=0),
                label="Bag skud",
                name="skydning_bag_skud"
            ),
            LabelSelect(
                *Options(*[str(i) for i in skud], selected_idx=0),
                label="Højre skud",
                name="skydning_hoejre_skud"
            ),
            LabelSelect(
                *Options(*[str(i) for i in skud], selected_idx=0),
                label="Spids skud",
                name="skydning_spids_skud"
            ),
        ),
        id="duerContainer"
    )

def getNavBar():
    return TabContainer(
             Li(A("Skydninger"), cls="uk-active", hx_get="/start", hx_target="body", hx_swap="outerHTML"),
             Li(A("Statistik"), hx_get="/statistik", hx_target="body", hx_swap="outerHTML"), alt=True
        )

@app.route("/opdaterSkydningType/{skydning_type}")
def opdaterSkydningType(skydning_type: str):
    if skydning_type == "40":
        sideduer = list(reversed(range(0, 11)))
        skud = ['10', '11', '12', '13', '14']
    else:
        sideduer = list(reversed(range(0, 7)))
        skud = ['6', '7', '8']

    return build_duer_grid(sideduer, skud)

@app.route("/sletSkydning/{skydning_id}")
def sletSkydning(session, skydning_id: int):
    userId = session.get(SESSION_TOKEN)
    if userId is None:
        return Container(
                    Body(
                        H1("Fejl"),
                        P("Du skal være logget ind for at slette en skydning."),
                        Button("Tilbage til start", hx_get="/start"), id="errorPage", style="text-align: center; padding: 50px; width: auto;"
                    ))
    success = deleteShootingData(skydning_id, userId)
    if not success:
        return Container(
                    Body(
                        H1("Fejl"),
                        P("Der opstod en fejl ved sletning af skydningen. Prøv igen senere."),
                        Button("Tilbage til start", hx_get="/start"), id="errorPage", style="text-align: center; padding: 50px; width: auto;"
                    ))
    return Redirect("/start")


@app.route("/")
def getLogin(session):
    return  Container(   
                    H1("Velkommen til Jagtskydningsappen!", cls="mb-4 text-3xl font-bold"),
                    P("Du kan oprette nye skydninger og se dine tidligere resultater."),
                    Br(),
                    Form(cls='space-y-6', hx_post="/login", hx_swap="outerHTML")(
                        LabelInput(label="Brugernavn", name="brugernavn", type="text", placeholder="Indtast dit brugernavn"),
                        LabelInput(label="Adgangskode", name="adgangskode", type="password", placeholder="Indtast din adgangskode"),
                        Button("Log ind", cls=ButtonT.primary, type="submit", hx_post="/login", hx_swap="outerHTML")
                    )
            )

@app.route("/login", methods=["POST"])
def login(session, brugernavn: str, adgangskode: str):
    userResp = getUserData(brugernavn, adgangskode)
    if not userResp:
        return Container(
                    Div(
                        H1("Fejl"),
                        P("Ugyldigt brugernavn eller adgangskode. Prøv igen."),
                        A("Tilbage til login", href="/", style="display: inline-block; margin: 10px; padding: 10px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;"),
                    )
        )
       
    session[SESSION_TOKEN] = userResp["id"]
    
    return Redirect("/start")
    
@app.route("/statistik")
def statistik(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    averages = getAverages(data)
    return Container(
                    H1("Statistik"),
                    Br(),
                    getNavBar(),
                    Card("Gennemsnit per anledning",
                         Table(
                             Thead(
                                 Tr(
                                    Th("Anledning"),
                                    Th("Ramte"),
                                    Th("Skud"),
                                    Th("Venstre"),
                                    Th("Venstre skud"),
                                    Th("Højre"),
                                    Th("Højre skud"),
                                    Th("Bag"),
                                    Th("Bag skud"),
                                    Th("Spids"),
                                    Th("Spids skud")
                                 )
                             ),
                             Tbody(*[Tr(
                                    Td(occasion["occasion"]),
                                    Td(str(round(occasion["result_hit"],2))),
                                    Td(str(round(occasion["result_shots"],2))),
                                    Td(str(round(occasion["venstre"],2))),
                                    Td(str(round(occasion["venstre_skud"],2))),
                                    Td(str(round(occasion["hoejre"],2))),
                                    Td(str(round(occasion["hoejre_skud"],2))),
                                    Td(str(round(occasion["bag"],2))),
                                    Td(str(round(occasion["bag_skud"],2))),
                                    Td(str(round(occasion["spids"],2))),
                                    Td(str(round(occasion["spids_skud"],2)))
                                ) for occasion in averages["occasion_averages"]]), id="occasionAveragesTable"
                         )
                    ),
                    Card("Gennemsnit per sted",
                            Table(
                                Thead(
                                    Tr(
                                        Th("Sted"),
                                        Th("Ramte"),
                                        Th("Skud"),
                                        Th("Venstre"),
                                        Th("Venstre skud"),
                                        Th("Højre"),
                                        Th("Højre skud"),
                                        Th("Bag"),
                                        Th("Bag skud"),
                                        Th("Spids"),
                                        Th("Spids skud")
                                    )
                                ),
                                Tbody(*[Tr(
                                        Td(location["place"]),
                                        Td(str(round(location["result_hit"],2))),
                                        Td(str(round(location["result_shots"],2))),
                                        Td(str(round(location["venstre"],2))),
                                        Td(str(round(location["venstre_skud"],2))),
                                        Td(str(round(location["hoejre"],2))),
                                        Td(str(round(location["hoejre_skud"],2))),
                                        Td(str(round(location["bag"],2))),
                                        Td(str(round(location["bag_skud"],2))),
                                        Td(str(round(location["spids"],2))),
                                        Td(str(round(location["spids_skud"],2)))
                                    ) for location in averages["location_averages"]]), id="locationAveragesTable"
                            )
                    ),
                    Card("Gennemsnit samlet",
                            Table(
                                Thead(
                                    Tr(
                                        Th("Ramte"),
                                        Th("Skud"),
                                        Th("Venstre"),
                                        Th("Venstre skud"),
                                        Th("Højre"),
                                        Th("Højre skud"),
                                        Th("Bag"),
                                        Th("Bag skud"),
                                        Th("Spids"),
                                        Th("Spids skud")
                                    )
                                ),
                                Tbody(
                                    Tr(
                                        Td(str(round(averages["normal_averages"]["result_hit"],2))),
                                        Td(str(round(averages["normal_averages"]["result_shots"],2))),
                                        Td(str(round(averages["normal_averages"]["venstre"],2))),
                                        Td(str(round(averages["normal_averages"]["venstre_skud"],2))),
                                        Td(str(round(averages["normal_averages"]["hoejre"],2))),
                                        Td(str(round(averages["normal_averages"]["hoejre_skud"],2))),
                                        Td(str(round(averages["normal_averages"]["bag"],2))),
                                        Td(str(round(averages["normal_averages"]["bag_skud"],2))),
                                        Td(str(round(averages["normal_averages"]["spids"],2))),
                                        Td(str(round(averages["normal_averages"]["spids_skud"],2)))
                                    )                                
                                ), id="overallAveragesTable"
                        ), id="statistikPage"
                    )
            )
                
                         


@app.route("/start")
def startPage(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    averages = getAverages(data)
    return Container(
                    H1("Velkommen til Jagtskydningsappen!"),
                    Br(),
                    Button("Opret ny skydning", cls=ButtonT.primary, data_uk_toggle="target: #nySkydning"),
                    nySkydning(),
                    Br(),
                    getNavBar(),
                    Br(),
                    Card("Seneste skydninger",
                        Table(
                            Thead(
                                Tr(
                                    Th("Sted"),
                                    Th("Dato"),
                                    Th("Anledning"),
                                    Th("40/24"),
                                    Th("Ramte"),
                                    Th("Skud"),
                                    Th("Venstre"),
                                    Th("Venstre skud"),
                                    Th("Højre"),
                                    Th("Højre skud"),
                                    Th("Bag"),
                                    Th("Bag skud"),
                                    Th("Spids"),
                                    Th("Spids skud"),
                                    Th(" ")
                                )
                            ),
                            Tbody(*[tilFoejSkydniner(entry) for entry in data]), id="skydningTable"
                        )
                    )
                )


def nySkydning():
    return Modal(
        Div(cls='p-6')(
            ModalTitle("Opret ny skydning", cls="mb-4 text-2xl font-bold text-center"),
            Br(),
            FormLabel("Runde"), DivLAligned(Radio(name="skydning_type", value="40", checked=True, hx_get="/opdaterSkydningType/40", hx_target="#duerContainer", hx_trigger="change")("40"),
                                            Radio(name="skydning_type", value="24", hx_get="/opdaterSkydningType/24", hx_target="#duerContainer", hx_trigger="change")("24")), 
            Br(),
            Form(cls='space-y-6', hx_post="/gemSkydning", hx_swap="outerHTML")(
                TextArea(label="Sted", name="skydning_sted", placeholder="Indtast sted for skydning"),
                LabelInput(label="Dato", name="skydning_dato", type="date"),
                LabelSelect(
                    *Options(*[str(i) for i in getAnledninger()], selected_idx=1, disabled_idxs={0}), label="Anledning", name="skydning_occation"
                ),

                build_duer_grid(DropDown_Sideduer_default, DropDown_Skud_default)
                ,
                DivRAligned(
                    ModalCloseButton("Anuller", cls=ButtonT.ghost),
                    Button("Gem skydning", cls=ButtonT.primary, type="submit", hx_post="/gemSkydning", hx_swap="outerHTML"), cls='space-x-2'
                )
            )
        ), id="nySkydning", open=False
    )

@app.route("/gemSkydning", methods=["POST"])
def gemSkydning(session, skydning_sted: str, skydning_dato: str, skydning_occation: str, skydning_venstre: int, skydning_venstre_skud: int, skydning_hoejre: int, skydning_hoejre_skud: int,
                   skydning_bag: int, skydning_bag_skud: int, skydning_spids: int, skydning_spids_skud: int):
    userId = session.get(SESSION_TOKEN)
    skydning_result_hit = skydning_venstre + skydning_hoejre + skydning_bag + skydning_spids
    skydning_result_shots = skydning_venstre_skud + skydning_hoejre_skud + skydning_bag_skud + skydning_spids_skud
    skydning_type = 40 if skydning_result_hit > 24 else 24
    saved = saveShootingData(skydning_sted, userId, skydning_dato, skydning_occation, int(skydning_type), skydning_result_hit, skydning_result_shots,
                              skydning_venstre, skydning_venstre_skud, skydning_hoejre, skydning_hoejre_skud, skydning_bag, skydning_bag_skud, skydning_spids, skydning_spids_skud)
    # show a new error modal if saving failed, otherwise redirect to start page
    if not saved:
        return Modal(
            Div(cls='p-6')(
                ModalTitle("Fejl", cls="mb-4 text-2xl font-bold text-center"),
                Br(),
                P("Der opstod en fejl ved gemning af skydningen. Prøv igen senere.", cls="text-center"),
                Br(),
                DivRAligned(
                    ModalCloseButton("Luk", cls=ButtonT.ghost),
                    Button("Tilbage til start", cls=ButtonT.primary, hx_get="/start", hx_swap="outerHTML"), cls='space-x-2'
                )
            ), id="errorModal", open=True
        )
    return Redirect("/start")

if __name__ == "__main__":
    serve()