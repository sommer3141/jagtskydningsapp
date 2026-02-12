import os
from dotenv import load_dotenv
from fasthtml.common import *
from supabase import create_client
from hashlib import sha256

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SESSION_TOKEN = "jagtskydningsapp_token"

DropDown_Sideduer = range(0,11)
DropDown_Skud = range(6,15)
        
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app, rt = fast_app(secret_key="superhemmeligkey")

def getDropDownShots():
    return [Option(str(i), value=str(i)) for i in DropDown_Skud]

def getDropDownHits():
    return [Option(str(i), value=str(i)) for i in DropDown_Sideduer.__reversed__()]

def getShootingData(userId: int = None):
    if userId is None:
        return []
    try:
        response = supabase.table("skydning").select("*").eq("userId", userId).execute()
    except Exception as e:
        print(f"Fejl ved hentning af data: {e}")
        return []
    return response.data
    
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

def getHead():
    return Head(
        Title("Jagtskydningsapp", style="text-align: center; padding: 10px; width: 100%; position: fixed; top: 0;"), id="head", 
    )

def getFoot():
    return Footer(
        P("Udviklet af Rolf Sommer. Ved spørgsmål, kontakt 60125444 eller send mail til rolf3141@gmail.com"), id="footer", class_="footer", style="text-align: center; padding: 10px; width: 100%; position: fixed; bottom: 0;"
    )

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
    )

@app.route("/")
def getLogin(session):
    print(f"Session ved login: {session}")
    return Html(getHead(),
                Body(
                    H1("Velkommen til Jagtskydningsappen!"),
                    P("Du kan oprette nye skydninger, se dine tidligere resultater og få tips til at forbedre din præcision."),
                    Form(
                        Fieldset(
                        Div(Input(name="brugernavn", type="text", placeholder="Brugernavn", style="padding: 5px; margin: 5px;",)),
                         Div(Input(name="adgangskode", type="password", placeholder="Adgangskode", style="padding: 5px; margin: 5px;"))
                         , Button("Log ind", type="submit", style="padding: 5px; margin: 5px;")),
                             method="post", hx_on__after_request="this.reset()", hx_swap="outerHTML", action="/login"
                        ), id="loginPage"
                )
                , getFoot())

@app.route("/login", methods=["POST"])
def login(session, brugernavn: str, adgangskode: str):
    userResp = getUserData(brugernavn, adgangskode)
    if not userResp:
        return Html(getHead(),
                    Body(
                        H1("Fejl"),
                        P("Ugyldigt brugernavn eller adgangskode. Prøv igen."),
                        A("Tilbage til login", href="/", style="display: inline-block; margin: 10px; padding: 10px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;"),
                    ), getFoot())
       
    session[SESSION_TOKEN] = userResp["id"]
    
    return Redirect("/start")
    

@app.route("/start")
def startPage(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    return Html(getHead(),
                Body(
                    H1("Velkommen til Jagtskydningsappen!"),
                    P("Du kan oprette nye skydninger, se dine tidligere resultater g på sigt måske fået noget utroligt sigende og mega sandt statistik :D ."),
                    A("Opret ny skydning", href="/nySkydning", style="display: inline-block; margin: 10px; padding: 10px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;"),
                    P(),
                    Table(
                        Thead(
                            Tr(
                                Th("Sted", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Dato", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Anledning", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("40/24", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Ramte", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Skud", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Venstre", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Venstre skud", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Højre", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Højre skud", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Bag", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Bag skud", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Spids", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;"),
                                Th("Spids skud", style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;")
                            )
                        ),
                        Tbody(*[tilFoejSkydniner(entry) for entry in data]), style="width: auto; border-collapse: collapse; border: 1px solid black; padding: 5px; margin: 5px;", id="skydningTable"
                    ), id="startPage"
                )
                , getFoot())


@app.route("/nySkydning")
def nySkydning(session):
    userId = session.get(SESSION_TOKEN)
    return Html(getHead(),
                Body(
                    H1("Opret ny skydning"),
                    Form(
                        Fieldset(
                            Div(Input(name="skydning_sted", type="text", placeholder="Sted", style="padding: 5px; margin: 5px;",)),
                            Div(Input(name="skydning_dato", type="date", style="padding: 5px; margin: 5px;")),
                            Div(Select(Option("Træning", value="Træning"), Option("Tavle", value="Tavle"), Option("DM", value="DM"), Option("Femkant", value="Femkant"), Option("Grand Prix", value="Grand Prix"),
                                                    Option("Hold DM", value="Hold DM"), Option("Andet Konkurrence", value="Andet Konkurrence"), Option("Andet", value="Andet"),
                                                    name="skydning_occation", placeholder="Anledning", style="padding: 5px; margin: 5px;",)),
                            Div(Select(Option(40), Option(24), name="skydning_type", style="padding: 5px; margin: 5px;", placeholder="40/24"), Label("40/24")),
                            Div(Select(getDropDownHits(),name="skydning_venstre", placeholder="Venstre", style="padding: 5px; margin: 5px;"), Label("Venstre")),
                            Div(Select(getDropDownShots(),name="skydning_venstre_skud", type="number", placeholder="Venstre skud", style="padding: 5px; margin: 5px;"), Label("Venstre skud")),
                            Div(Select(getDropDownHits(),name="skydning_hoejre", placeholder="Højre", style="padding: 5px; margin: 5px;"), Label("Højre")),
                            Div(Select(getDropDownShots(),name="skydning_hoejre_skud", type="number", placeholder="Højre skud", style="padding: 5px; margin: 5px;"), Label("Højre skud")),
                            Div(Select(getDropDownHits(),name="skydning_bag", placeholder="Bag", style="padding: 5px; margin: 5px;" ), Label("Bag")),
                            Div(Select(getDropDownShots(),name="skydning_bag_skud", type="number", placeholder="Bag skud", style="padding: 5px; margin: 5px;"), Label("Bag skud")),
                            Div(Select(getDropDownHits(),name="skydning_spids", placeholder="Spids", style="padding: 5px; margin: 5px;"), Label("Spids")),
                            Div(Select(getDropDownShots(),name="skydning_spids_skud", type="number", placeholder="Spids skud", style="padding: 5px; margin: 5px;"), Label("Spids skud")),        
                            Button("Gem skydning", type="submit", style="padding: 5px; margin: 5px;")
                        ), method="post", hx_on__after_request="this.reset()", hx_swap="outerHTML", action="/gemSkydning", hx_target="#startPage"
                    ), id="nySkydningPage"
                )
                , getFoot())

@app.route("/gemSkydning", methods=["POST"])
def gemSkydning(session, skydning_sted: str, skydning_dato: str, skydning_occation: str, skydning_type: str, skydning_venstre: int, skydning_venstre_skud: int, skydning_hoejre: int, skydning_hoejre_skud: int,
                   skydning_bag: int, skydning_bag_skud: int, skydning_spids: int, skydning_spids_skud: int):
    userId = session.get(SESSION_TOKEN)
    skydning_result_hit = skydning_venstre + skydning_hoejre + skydning_bag + skydning_spids
    skydning_result_shots = skydning_venstre_skud + skydning_hoejre_skud + skydning_bag_skud + skydning_spids_skud
    saved = saveShootingData(skydning_sted, userId, skydning_dato, skydning_occation, int(skydning_type), skydning_result_hit, skydning_result_shots,
                              skydning_venstre, skydning_venstre_skud, skydning_hoejre, skydning_hoejre_skud, skydning_bag, skydning_bag_skud, skydning_spids, skydning_spids_skud)
    if not saved:
        return Html(getHead(),
                    Body(
                        H1("Fejl"),
                        P("Der opstod en fejl ved gemning af skydningen. Prøv igen senere."),
                        Button("Tilbage til start", hx_get="/start"), id="errorPage"
                    ), getFoot())
    return Redirect("/start")

if __name__ == "__main__":
    serve()