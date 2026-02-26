import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
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

app, rt = fast_app(secret_key="superhemmeligkey", hdrs=Theme.blue.headers(), dark_mode=True)

def getSkydebaner():
    try:
        response = supabase.from_("skydebaner").select("*").order("name", desc=False).execute()
    except Exception as e:
        print(f"Fejl ved hentning af skydebaner: {e}")
        return []
    return response.data

## hent skydebaner ved opstart og gem i en global variabel for at undgå unødvendige databasekald
skydebaner = getSkydebaner()

def getShootingData(userId: int = None):
    if userId is None:
        return []
    try:
        response = supabase.from_("skydning") \
            .select("*, skydebaner(*), vejr(*)") \
            .eq("userId", userId) \
            .order("date", desc=True) \
            .execute()
    except Exception as e:
        print(f"Fejl ved hentning af data: {e}")
        return []
    return response.data

def getweatherData(latitude: float, longitude: float, datetime: str):
    date = datetime.split("T")[0]
    hour = datetime.split("T")[1].split(":")[0] if "T" in datetime else "00"
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={date}&end_date={date}&hourly=temperature_2m,cloud_cover,wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=CET"
        response = requests.get(url)
    except Exception as e:
        print(f"Fejl ved hentning af vejrdata: {e}")
        return None
    data = response.json()
    if "hourly" not in data:
        print("Ingen vejrdata tilgængelig for denne dato og lokation.")
        return None
    for weatherDate in data["hourly"]["time"]:
            weatherTime = weatherDate.split("T")[1] if "T" in weatherDate else "00:00"
            weatherHour = weatherTime.split(":")[0]
            if weatherHour == hour:
                index = data["hourly"]["time"].index(weatherDate)
                return data["hourly"]["temperature_2m"][index], data["hourly"]["cloud_cover"][index], data["hourly"]["wind_speed_10m"][index], data["hourly"]["wind_direction_10m"][index]
    print("Ingen vejrdata fundet for det specifikke tidspunkt.")
    return None

def getAnledninger():
    return ["Vælg anledning", "Træning", "Tavle", "DM", "Femkant", "Grand Prix", "Amtsturnering", "Hold DM", "Andet Konkurrence", "Andet"]

def deleteShootingData(skydning_id: int, userId: int = None):
    try:
        response = supabase.table("vejr").delete().eq("skydnings_id", skydning_id).execute()
        response = supabase.table("skydning").delete().eq("id", skydning_id).eq("userId", userId).execute()
    except Exception as e:
        print(f"Fejl ved sletning af data: {e}")
        return False
    return True

def getAverages(df):
    if df.empty:
        return {}

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
    }).round(2).reset_index()

    location_averages = df.groupby("skydebaner.name").agg({
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
    }).round(2).reset_index()
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
    }).round(2).to_frame().T
    return {
        "occasion_averages": occasion_averages.to_dict(orient="records"),
        "location_averages": location_averages.to_dict(orient="records"),
        "normal_averages": normal_averages.to_dict(orient="records")[0]
    }

def getPercentages(df):
    numberOfEntries = len(df)
    if numberOfEntries == 0:
        return {}
    
    occasion_percentages = df.groupby("occasion").agg({
        "result_hit": "sum",
        "result_shots": "sum",
        "venstre": "sum",
        "venstre_skud": "sum",
        "hoejre": "sum",
        "hoejre_skud": "sum",
        "bag": "sum",
        "bag_skud": "sum",
        "spids": "sum",
        "spids_skud": "sum"
    }).reset_index()
    location_percentages = df.groupby("skydebaner.name").agg({
        "result_hit": "sum",
        "result_shots": "sum",
        "venstre": "sum",
        "venstre_skud": "sum",
        "hoejre": "sum",
        "hoejre_skud": "sum",
        "bag": "sum",
        "bag_skud": "sum",
        "spids": "sum",
        "spids_skud": "sum"
    }).reset_index()
    normal_percentages = df.agg({
        "result_hit": "sum",
        "result_shots": "sum",
        "venstre": "sum",
        "venstre_skud": "sum",
        "hoejre": "sum",
        "hoejre_skud": "sum",
        "bag": "sum",
        "bag_skud": "sum",
        "spids": "sum",
        "spids_skud": "sum"
    }).to_frame().T

    numberOfPossibleHits = numberOfEntries * 40
    numberOfPossibleSideHits = numberOfEntries * 10
    occasion_percentages["result_hit"] = (occasion_percentages["result_hit"] / numberOfPossibleHits * 100).round(2)
    occasion_percentages["venstre"] = (occasion_percentages["venstre"] / numberOfPossibleSideHits * 100).round(2)
    occasion_percentages["hoejre"] = (occasion_percentages["hoejre"] / numberOfPossibleSideHits * 100).round(2)
    occasion_percentages["bag"] = (occasion_percentages["bag"] / numberOfPossibleSideHits * 100).round(2)
    occasion_percentages["spids"] = (occasion_percentages["spids"] / numberOfPossibleSideHits * 100).round(2)
    location_percentages["result_hit"] = (location_percentages["result_hit"] / numberOfPossibleHits * 100).round(2)
    location_percentages["venstre"] = (location_percentages["venstre"] / numberOfPossibleSideHits * 100).round(2)
    location_percentages["hoejre"] = (location_percentages["hoejre"] / numberOfPossibleSideHits * 100).round(2)
    location_percentages["bag"] = (location_percentages["bag"] / numberOfPossibleSideHits * 100).round(2)
    location_percentages["spids"] = (location_percentages["spids"] / numberOfPossibleSideHits * 100).round(2)
    normal_percentages["result_hit"] = (normal_percentages["result_hit"] / numberOfPossibleHits * 100).round(2)
    normal_percentages["venstre"] = (normal_percentages["venstre"] / numberOfPossibleSideHits * 100).round(2)
    normal_percentages["hoejre"] = (normal_percentages["hoejre"] / numberOfPossibleSideHits * 100).round(2)
    normal_percentages["bag"] = (normal_percentages["bag"] / numberOfPossibleSideHits * 100).round(2)
    normal_percentages["spids"] = (normal_percentages["spids"] / numberOfPossibleSideHits * 100).round(2)
    return {
        "occasion_percentages": occasion_percentages.to_dict(orient="records"),
        "location_percentages": location_percentages.to_dict(orient="records"),
        "normal_percentages": normal_percentages.to_dict(orient="records")[0]
    }

def createFormGraph(data):
    df = pd.DataFrame(data)
    df = df[df['type'] == 40]
    avg = df['result_hit'].mean().round(2) if not df.empty else 0
    last10 = df.sort_values("date", ascending=False).head(10)
    last10 = last10[['date', 'result_hit']]
    #trend
    x = np.arange(len(last10))
    y = last10["result_hit"]
    coef = np.polyfit(x, y, 1)
    trend = np.poly1d(coef)(x).round(2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["result_hit"], mode="markers + lines", name="Resultater", marker=dict(color='LightSkyBlue', size=10)))
    fig.add_trace(go.Scatter(x=df["date"], y=[avg]*len(df), mode="lines", name="Gennemsnit", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=df["date"], y=trend, mode="lines", name="Trendline", line=dict(dash="dot")))

    fig.update_layout(
        template="plotly_dark",
        title="Formkurve – Seneste 10 skydninger",
        xaxis_title="Dato",
        yaxis_title="Score"
    )

    # Export til HTML div
    graph_html = fig.to_html(full_html=False)

    return Titled("Formkurve",
        Card(
            Safe(graph_html),
            cls="p-6 rounded-2xl shadow-xl"
        )
    )


def createTable(headers, df, value_keys, delete_key=None, delete_url=None):
    return Table(cls="border-collapse border border-gray-100 table-auto")(
        Thead(
            Tr(*[Th(header, cls="text-left border text-bold") for header in headers])
        ),
        Tbody(
            *[Tr(*[Td(row[key], cls="text-left border") for key in value_keys]) for _, row in df.iterrows()]
            # add delete button if delete_key and delete_url are provided
            + ([Tr(Td(A("Slet", href=delete_url + str(row[delete_key])))) for _, row in df.iterrows()] if delete_key and delete_url else [])
        )
    )

def calculateTavleScore(df):
    df = df[df["occasion"] == "Tavle"].sort_values("result_hit", ascending=False).sort_values("result_shots", ascending=True).head(15)
    return df["result_hit"].sum(), df["result_shots"].sum()

def getTotalHitsAndShots(df):
    totalHits = df["result_hit"].sum()
    totalShots = df["result_shots"].sum()
    return totalHits, totalShots

def findSkydebaneInfo(place_name):
    for skydebane in skydebaner:
        if skydebane["name"] == place_name:
            return skydebane["id"], skydebane["latitude"], skydebane["longitude"]
    return None

def saveShootingData(place: str, useriD: int, date: str, occation: str, type: int, result_hit: int, result_shot: int, venstre :int, venstre_skud: int, hoejre: int, hoejre_skud: int, bag: int , bag_skud: int, spids: int, spids_skud: int):
    skydebaneId, lat, lon = findSkydebaneInfo(place)
    if skydebaneId is None:
        print(f"Skydebane '{place}' ikke fundet i databasen.")
        return False
    temp, cloudCover, wind_speed, wind_direction = getweatherData(lat, lon, date) or (None, None, None, None)
    try:
        response = supabase.table("skydning").insert({
            "place_id": skydebaneId,
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
        shooting_id = response.data[0]["id"]
        if temp is not None and cloudCover is not None and wind_speed is not None and wind_direction is not None:
            supabase.table("vejr").insert({
                "skydnings_id": shooting_id,
                "temp": temp,
                "skydaekke": cloudCover,
                "vind": wind_speed,
                "vind_dir": wind_direction
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
        Td(entry["skydebaner"]["name"], cls="border text-base"),
        Td(entry["date"], cls="border text-base"),
        Td(entry["occasion"], cls="border text-base"),
        Td(str(entry["type"]), cls="border text-base"),
        Td(str(entry["result_hit"]), cls="border text-base"),
        Td(str(entry["result_shots"]), cls="border text-base"),
        Td(str(entry["venstre"]), cls="border text-base"), 
        Td(str(entry["venstre_skud"]), cls="border text-base"), 
        Td(str(entry["hoejre"]), cls="border text-base"), 
        Td(str(entry["hoejre_skud"]), cls="border text-base"), 
        Td(str(entry["bag"]), cls="border text-base"), 
        Td(str(entry["bag_skud"]), cls="border text-base"), 
        Td(str(entry["spids"]), cls="border text-base"), 
        Td(str(entry["spids_skud"]), cls="border text-base"),
        Td(A("Slet", href=f"/sletSkydning/{entry['id']}", cls="inline-block m-1 p-1 bg-blue-500 text-white no-underline rounded"), cls="border text-base")
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

def getDataframeFromData(data):
    if not data:
        return {}
    df_raw = pd.DataFrame(data)
    df = df_raw.copy()
    if df_raw.empty:
        return {}
    try:
        df_skydebaner = pd.json_normalize(df_raw["skydebaner"]).add_prefix("skydebaner.")
        df = df_raw.drop(columns=["skydebaner"]).join(df_skydebaner)
    except Exception as e:
        df.drop(columns=["skydebaner"], inplace=True)
    
    try:    
        df_vejr = pd.json_normalize(df_raw["vejr"]).add_prefix("vejr.")
        df = pd.concat([df.drop(columns=["vejr"]), df_vejr], axis=1)
    except Exception as e:
        df.drop(columns=["vejr"], inplace=True)     
    
    df = df[df['type'] == 40]
    return df
    
@app.route("/statistik")
def statistik(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    df = getDataframeFromData(data)
    
    averages = getAverages(df)
    percetages = getPercentages(df)
    tavleHits, tavleShots = calculateTavleScore(df)
    totalHits, totalShots = getTotalHitsAndShots(df)
    resultHeaders = ["Ramte", "Skud", "Venstre", "Venstre skud", "Højre", "Højre skud", "Bag", "Bag skud", "Spids", "Spids skud"]
    percentageHeaders = ["Ramte %", "Venstre %", "Højre %", "Bag %", "Spids %"]
    resultValueKeys = ["result_hit", "result_shots", "venstre", "venstre_skud", "hoejre", "hoejre_skud", "bag", "bag_skud", "spids", "spids_skud"]
    percentageValueKeys = ["result_hit", "venstre", "hoejre", "bag", "spids"]
    return Container(
                    H1("Statistik"),
                    Br(),
                    getNavBar(),
                    Br(),
                    Grid(
                        Card(H4(str(round(tavleHits,2)) + "/" + str(round(tavleShots,2))), header=H3("Tavle resultater", cls="text-xl font-bold")),
                        Card(H4(str(round(totalHits,2)) + "/" + str(round(totalShots,2))), header=H3("Total resultater", cls="text-xl font-bold")),
                        Card(H4(str(round(totalHits/totalShots*100,2)) + "%"), header=H3("Total %", cls="text-xl font-bold"))
                    ),
                    Br(),
                    createFormGraph(data),
                    Br(),
                    Div("Resultater per anledning", cls="divider text-2xl font-bold"),
                    Card("Gennemsnit per anledning", cls="font-bold text-center")(
                        createTable(["Anledning"] + resultHeaders, pd.DataFrame(averages["occasion_averages"]), ["occasion"] + resultValueKeys)
                    ),
                    Card("Procenter per anledning", cls="font-bold text-center")(
                        createTable(["Anledning"] + percentageHeaders, pd.DataFrame(percetages["occasion_percentages"]), ["occasion"] + percentageValueKeys)
                    ),
                    Br(),
                    Div("Resultater per sted", cls="divider text-2xl font-bold"),
                    Card("Gennemsnit per sted", cls="font-bold text-center")(
                            createTable(["Sted"] + resultHeaders, pd.DataFrame(averages["location_averages"]), ["skydebaner.name"] + resultValueKeys)
                    ),
                    Card("Procenter per sted", cls="font-bold text-center")(
                        createTable(["Sted"] + percentageHeaders, pd.DataFrame(percetages["location_percentages"]), ["skydebaner.name"] + percentageValueKeys)
                    ),
                    Br(),
                    Div("Resultater samlet", cls="divider text-2xl font-bold"),
                    Card("Gennemsnit samlet", cls="font-bold text-center")(
                            createTable(resultHeaders, pd.DataFrame([averages["normal_averages"]]), resultValueKeys)
                    ),
                    Card("Overall procenter", cls="font-bold text-center")(
                        createTable(percentageHeaders, pd.DataFrame([percetages["normal_percentages"]]), percentageValueKeys)
                    )
            )
                
                         


@app.route("/start")
def startPage(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    headers = ["Sted", "Dato", "Anledning", "40/24", "Ramte", "Skud", "Venstre", "Venstre skud", "Højre", "Højre skud", "Bag", "Bag skud", "Spids", "Spids skud", ""]
    value_keys = ["place_id", "date", "occasion", "type", "result_hit", "result_shots", "venstre", "venstre_skud", "hoejre", "hoejre_skud", "bag", "bag_skud", "spids", "spids_skud"]
    return Container(
                    H1("Velkommen til Jagtskydningsappen!"),
                    Br(),
                    Button("Opret ny skydning", cls=ButtonT.primary, data_uk_toggle="target: #nySkydning"),
                    nySkydning(),
                    Br(),
                    getNavBar(),
                    Br(),
                    Card("Seneste skydninger", cls="font-bold text-center text-2xl")(
                        Table(
                            Thead(
                                Tr(cls="font-bold text-left")(
                                    Th("Sted", cls="text-left border text-lg"),
                                    Th("Dato", cls="text-left border text-lg"),
                                    Th("Anledning", cls="text-left border text-lg"),
                                    Th("40/24", cls="text-left border text-lg"),
                                    Th("Ramte", cls="text-left border text-lg"),
                                    Th("Skud", cls="text-left border text-lg"),
                                    Th("Venstre", cls="text-left border text-lg"),
                                    Th("Venstre skud", cls="text-left border text-lg"),
                                    Th("Højre", cls="text-left border text-lg"),
                                    Th("Højre skud", cls="text-left border text-lg"),
                                    Th("Bag", cls="text-left border text-lg"),
                                    Th("Bag skud", cls="text-left border text-lg"),
                                    Th("Spids", cls="text-left border text-lg"),
                                    Th("Spids skud", cls="text-left border text-lg"),
                                    Th(" ", cls="text-left border text-lg")
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
                LabelSelect(*Options(*[str(skydebane["name"]) for skydebane in skydebaner]), label="Sted", name="skydning_sted"),
                LabelInput(label="Dato", name="skydning_dato", type="datetime-local"),
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