import os
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
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

app, rt = fast_app(secret_key="superhemmeligkey", hdrs=Theme.blue.headers(), dark_mode=True, redirect_slashes=False)

def AppLayout(*content, title=None):
    return Container(
        Div(
            H1(title, cls="text-2xl md:text-3xl font-bold mb-6") if title else None,
            *content,
            cls="max-w-5xl mx-auto px-4 py-6 space-y-6"
        )
    )

def translateWeatherCode(code):
    weather_mapping = {
        0: "Klar himmel",
        1: "Hovedsageligt klar himmel",
        2: "Delvist skyet",
        3: "Overskyet",
        45: "Tåge",
        48: "Tåge med rimfrost",
        51: "Let regn",
        53: "Moderat regn",
        55: "Kraftig regn",
        56: "Let frysende regn",
        57: "Kraftig frysende regn",
        61: "Let regnbyge",
        63: "Moderat regnbyge",
        65: "Kraftig regnbyge",
        66: "Let frysende regnbyge",
        67: "Kraftig frysende regnbyge",
        71: "Let snebyge",
        73: "Moderat snebyge",
        75: "Kraftig snebyge",
        77: "Snegryn",
        80: "Let regnbyge (lokalt)",
        81: "Moderat regnbyge (lokalt)",
        82: "Kraftig regnbyge (lokalt)",
        85: "Let snebyge (lokalt)",
        86: "Kraftig snebyge (lokalt)",
        95: "Tordenvejr",
        96: "Tordenvejr med let  hagl",
        99: "Tordenvejr med kraftig hagl"
    }
    return weather_mapping.get(code, "Ukendt vejr")

def getSkydebaner():
    try:
        response = supabase.from_("skydebaner").select("*").order("name", desc=False).execute()
    except Exception as e:
        print(f"Fejl ved hentning af skydebaner: {e}")
        return []
    return response.data

## hent skydebaner ved opstart og gem i en global variabel for at undgå unødvendige databasekald
skydebaner = getSkydebaner()

def GetWindDirection(degrees):
    directions = ["N", "NØ", "Ø", "SØ", "S", "SV", "V", "NV"]
    idx = round(degrees / 45) % 8
    return directions[idx]

def getShootingData(userId: int = None):
    if userId is None:
        return []
    try:
        response = supabase.from_("skydning") \
            .select("*, skydebaner(name), vejr(temp, skydaekke, vind, vind_dir, weather_code)") \
            .eq("userId", userId) \
            .order("date", desc=True) \
            .execute()
    except Exception as e:
        print(f"Fejl ved hentning af data: {e}")
        return []
    return response.data

def getSingleShootingData(skydning_id: int):
    try:
        response = supabase.from_("skydning") \
            .select("*, skydebaner(name), vejr(temp, skydaekke, vind, vind_dir, weather_code)") \
            .eq("id", skydning_id) \
            .execute()
    except Exception as e:
        print(f"Fejl ved hentning af data: {e}")
        return None
    return response.data[0] if response.data else None

def getweatherData(latitude: float, longitude: float, datetime: str):
    date = datetime.split("T")[0]
    hour = datetime.split("T")[1].split(":")[0] if "T" in datetime else "00"
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={date}&end_date={date}&hourly=temperature_2m,cloud_cover,wind_speed_10m,wind_direction_10m,weather_code&wind_speed_unit=ms&timezone=CET"
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
                return data["hourly"]["temperature_2m"][index], data["hourly"]["cloud_cover"][index], data["hourly"]["wind_speed_10m"][index], data["hourly"]["wind_direction_10m"][index], data["hourly"]["weather_code"][index]
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

def getPercentagesByWeather(df):
    if df.empty:
        return {}
    temp_percentages = df.groupby(pd.cut(df["vejr.temp"], bins=5)).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    cloud_percentages = df.groupby(pd.cut(df["vejr.skydaekke"], bins=5)).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    wind_speed_percentages = df.groupby(pd.cut(df["vejr.vind"], bins=3)).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    wind_dir_percentages = df.groupby(pd.cut(df["vejr.vind_dir"], bins=8)).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    weather_code_percentages = df.groupby("vejr.weather_code").agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    temp_percentages["vejr.temp"] = temp_percentages["vejr.temp"].apply(lambda x: x.mid.round(2))
    cloud_percentages["vejr.skydaekke"] = cloud_percentages["vejr.skydaekke"].apply(lambda x: x.mid.round(2))
    wind_speed_percentages["vejr.vind"] = wind_speed_percentages["vejr.vind"].apply(lambda x: x.mid.round(2))
    wind_dir_percentages["vejr.vind_dir"] = wind_dir_percentages["vejr.vind_dir"].apply(lambda x: GetWindDirection(x.mid))
    weather_code_percentages["vejr.weather_code"] = weather_code_percentages["vejr.weather_code"].apply(lambda x: translateWeatherCode(x))
    return {
        "temp_percentages": temp_percentages.to_dict(orient="records"),
        "cloud_percentages": cloud_percentages.to_dict(orient="records"),
        "wind_speed_percentages": wind_speed_percentages.to_dict(orient="records"),
        "wind_dir_percentages": wind_dir_percentages.to_dict(orient="records"),
        "weather_code_percentages": weather_code_percentages.to_dict(orient="records")
    }
    

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

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["result_hit"], mode="markers + lines", name="Resultater", marker=dict(color='LightSkyBlue', size=10)))
    fig.add_trace(go.Scatter(x=df["date"], y=[avg]*len(df), mode="lines", name="Gennemsnit", line=dict(dash="dash")))

    fig.update_layout(
        template="plotly_dark",
        title="Formkurve – Seneste 10 skydninger",
        xaxis_title="Dato",
        yaxis_title="Score"
    )

    # Export til HTML div
    graph_html = fig.to_html(full_html=False)

    return Card(
            Safe(graph_html),
            cls="p-6 rounded-2xl shadow-xl"
        )
        

def createStatsGraph(dataDict, title, xTitle, yTitle, Total=True, BarPlot=True):
    df = pd.DataFrame(dataDict)
    if Total:
        # only keep the two first colums
        df = df.iloc[:, :2]
    else:
        # remove the second column and keep the rest
        df = df.drop(df.columns[1], axis=1)


    fig = go.Figure()
    for column in df.columns[1:]:
        if BarPlot:
            fig.add_trace(go.Bar(x=df[df.columns[0]], y=df[column], name=column))
        else:
            fig.add_trace(go.Scatter(x=df[df.columns[0]], y=df[column], mode="markers + lines", name=column, marker=dict(size=10)))
    fig.update_layout(
        template="plotly_dark",
        title=title,
        xaxis_title=xTitle,
        yaxis_title=yTitle
    )

    graph_html = fig.to_html(full_html=False)

    return Card(
        Safe(graph_html),
        cls="p-6 rounded-2xl shadow-xl"
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
    df = df[df["occasion"] == "Tavle"].sort_values(["result_hit", "result_shots"], ascending=[False, True]).head(15)
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
    temp, cloudCover, wind_speed, wind_direction, weather_code = getweatherData(lat, lon, date) or (None, None, None, None, None)
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
                "vind_dir": wind_direction,
                "weather_code": weather_code
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
        Td(A(entry["skydebaner"]["name"], href=f"/visSkydning/{entry['id']}", cls="cursor-pointer hover:bg-gray-700"), cls="border text-base"),
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

def getNavBar(active):
    return TabContainer(
             Li(A("Skydninger"), cls="uk-active" if active == "Skydninger" else "", hx_get="/start", hx_target="body", hx_swap="outerHTML"),
             Li(A("Statistik"), cls="uk-active" if active == "Statistik" else "", hx_get="/statistik", hx_target="body", hx_swap="outerHTML"), alt=True
        )

def getStatsNavBar(active):
    def tab(name, label, url):
        return Li(
            A(label, href=url),
            cls="uk-active" if active == name else ""
        )

    return TabContainer(
        tab("Samlet", "Samlet", "/statistik"),
        tab("Anledning", "Anledning", "/statistik/anledning"),
        tab("Sted", "Sted", "/statistik/sted"),
        tab("Vejr", "Vejr", "/statistik/vejr"),
        alt=True
    )


def createStatsList(headers, df, value_keys, label_key=None):
    if df is None or df.empty:
        return Div(P("Ingen data", cls="text-sm text-gray-400"))

    cards = []
    for _, row in df.iterrows():
        title = row[label_key] if label_key else None
        items = [
            Div(
                P(header, cls="text-xs text-gray-400"),
                P(str(row.get(key, "")), cls="font-semibold")
            )
            for header, key in zip(headers, value_keys)
        ]
        cards.append(
            Card(cls="p-4 rounded-2xl shadow-md")(
                H3(str(title), cls="font-bold mb-4") if title else None,
                Grid(*items, cls="grid grid-cols-2 gap-3")
            )
        )
    return Div(*cards, cls="space-y-4")

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
    return AppLayout(

    Card(cls="p-6 rounded-3xl shadow-xl max-w-md mx-auto")(
        H2("Log ind", cls="text-xl font-bold text-center mb-4"),

        Form(cls="space-y-4", hx_post="/login", hx_swap="outerHTML")(
            LabelInput(label="Brugernavn", name="brugernavn"),
            LabelInput(label="Adgangskode", name="adgangskode", type="password"),
            Button("Log ind",
                   cls=ButtonT.primary + " w-full")
        )
    ),

    title="Velkommen"
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
    return AppLayout(

            getNavBar(active="Statistik"),
            Br(),
            getStatsNavBar(active="Samlet"),
            Br(),

            Grid(
                Card(cls="p-5 rounded-2xl shadow-lg text-center")(
                    P("Tavle", cls="text-gray-400"),
                    H2(f"{round(tavleHits,2)} / {round(tavleShots,2)}",
                    cls="text-2xl font-bold")
                ),
                Card(cls="p-5 rounded-2xl shadow-lg text-center")(
                    P("Total", cls="text-gray-400"),
                    H2(f"{round(totalHits,2)} / {round(totalShots,2)}",
                    cls="text-2xl font-bold")
                ),
                Card(cls="p-5 rounded-2xl shadow-lg text-center bg-blue-600 text-white")(
                    P("Total %", cls="text-blue-100"),
                    H2(f"{round(totalHits/totalShots*100,2)}%",
                    cls="text-3xl font-bold")
                ),
                cls="grid grid-cols-1 md:grid-cols-3 gap-4"
            ),

            createFormGraph(data),

            Br(),
            Div("Resultater samlet", cls="divider text-2xl font-bold"),
            Card("Gennemsnit samlet", cls="font-bold text-center mb-2")(
                createStatsList(resultHeaders, pd.DataFrame([averages["normal_averages"]]), resultValueKeys)
            ),
            Card("Overall procenter", cls="font-bold text-center mb-2")(
                createStatsList(percentageHeaders, pd.DataFrame([percetages["normal_percentages"]]), percentageValueKeys)
            )
            ,
            title="Statistik"
        )

@app.route("/statistik/anledning")
def statistikAnledning(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    df = getDataframeFromData(data)

    averages = getAverages(df)
    percetages = getPercentages(df)

    resultHeaders = ["Ramte", "Skud", "Venstre", "Venstre skud", "Højre", "Højre skud", "Bag", "Bag skud", "Spids", "Spids skud"]
    percentageHeaders = ["Ramte %", "Venstre %", "Højre %", "Bag %", "Spids %"]
    resultValueKeys = ["result_hit", "result_shots", "venstre", "venstre_skud", "hoejre", "hoejre_skud", "bag", "bag_skud", "spids", "spids_skud"]
    percentageValueKeys = ["result_hit", "venstre", "hoejre", "bag", "spids"]
    return AppLayout(
            getNavBar(active="Statistik"),

            Br(),
            getStatsNavBar(active="Anledning"),
            Br(),
            Div("Resultater per anledning", cls="divider text-2xl font-bold"),
            Card("Gennemsnit per anledning", cls="font-bold text-center mb-2")(
                createStatsList(resultHeaders, pd.DataFrame(averages["occasion_averages"]), resultValueKeys, label_key="occasion")
            ),
            Card("Procenter per anledning", cls="font-bold text-center mb-2")(
                createStatsList(percentageHeaders, pd.DataFrame(percetages["occasion_percentages"]), percentageValueKeys, label_key="occasion")
            ),
            title="Statistik"
        )         

@app.route("/statistik/sted")
def statistikSted(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    df = getDataframeFromData(data)

    averages = getAverages(df)
    percetages = getPercentages(df)

    resultHeaders = ["Ramte", "Skud", "Venstre", "Venstre skud", "Højre", "Højre skud", "Bag", "Bag skud", "Spids", "Spids skud"]
    percentageHeaders = ["Ramte %", "Venstre %", "Højre %", "Bag %", "Spids %"]
    resultValueKeys = ["result_hit", "result_shots", "venstre", "venstre_skud", "hoejre", "hoejre_skud", "bag", "bag_skud", "spids", "spids_skud"]
    percentageValueKeys = ["result_hit", "venstre", "hoejre", "bag", "spids"]
    return AppLayout(
            getNavBar(active="Statistik"),
            Br(),
            getStatsNavBar(active="Sted"),
            Br(),
            Div("Resultater per sted", cls="divider text-2xl font-bold"),
            Card("Gennemsnit per sted", cls="font-bold text-center mb-2")(
                createStatsList(resultHeaders, pd.DataFrame(averages["location_averages"]), resultValueKeys, label_key="skydebaner.name")
            ),
            Card("Procenter per sted", cls="font-bold text-center")(
                createStatsList(percentageHeaders, pd.DataFrame(percetages["location_percentages"]), percentageValueKeys, label_key="skydebaner.name")
            ),
            Br(),
            Div("Resultater samlet", cls="divider text-2xl font-bold"),
            Card("Gennemsnit samlet", cls="font-bold text-center mb-2")(
                createStatsList(resultHeaders, pd.DataFrame([averages["normal_averages"]]), resultValueKeys)
            ),
            title="Statistik"
        )
 
@app.route("/statistik/vejr")
def statistikVejr(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    df = getDataframeFromData(data)

    weatherDataPercentages = getPercentagesByWeather(df)

    return AppLayout(

            getNavBar(active="Statistik"),
            Br(),
            getStatsNavBar(active="Vejr"),
            Br(),
            
            Titled("Vejrstatistik for samlede resultater",
                   createStatsGraph(weatherDataPercentages["temp_percentages"], "Samlet resultater baseret på temperatur", "Temperatur (°C)", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["cloud_percentages"], "Samlet resultater baseret på sky-dække", "Sky-dække (%)", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["wind_speed_percentages"], "Samlet resultater baseret på vindhastighed", "Vindhastighed (m/s)", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["wind_dir_percentages"], "Samlet resultater baseret på vindretning", "Vindretning", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=True),
                   createStatsGraph(weatherDataPercentages["weather_code_percentages"], "Samlet resultater baseret på vejr", "Vejr", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=True),cls="mt-10"),
            Titled("Vejrstatistik for sideduer",
                   createStatsGraph(weatherDataPercentages["temp_percentages"], "Sideduer baseret på temperatur", "Temperatur (°C)", "Gennemsnitligt antal ramte side duer", Total=False, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["cloud_percentages"], "Sideduer baseret på sky-dække", "Sky-dække (%)", "Gennemsnitligt antal ramte side duer", Total=False, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["wind_speed_percentages"], "Sideduer baseret på vindhastighed", "Vindhastighed (m/s)", "Gennemsnitligt antal ramte side duer", Total=False, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["wind_dir_percentages"], "Sideduer baseret på vindretning", "Vindretning", "Gennemsnitligt antal ramte side duer", Total=False, BarPlot=True),
                   createStatsGraph(weatherDataPercentages["weather_code_percentages"], "Sideduer baseret på vejr", "Vejr", "Gennemsnitligt antal ramte side duer", Total=False, BarPlot=True),
                    cls="mt-10"),
            title="Statistik"
        )

                         


@app.route("/start")
def startPage(session):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
 #   headers = ["Sted", "Dato", "Anledning", "40/24", "Ramte", "Skud", "Venstre", "Venstre skud", "Højre", "Højre skud", "Bag", "Bag skud", "Spids", "Spids skud", ""]
 #   value_keys = ["place_id", "date", "occasion", "type", "result_hit", "result_shots", "venstre", "venstre_skud", "hoejre", "hoejre_skud", "bag", "bag_skud", "spids", "spids_skud"]
    return AppLayout(

        # Top action card
        Card(cls="p-5 rounded-3xl shadow-lg bg-gradient-to-br from-blue-600 to-blue-800 text-white")(
            H2("Jagtskydningsappen", cls="text-xl font-semibold"),
            P("Hold styr på dine resultater og din form", cls="text-blue-100"),
            Br(),
            Button("➕ Opret ny skydning",
                cls="bg-white text-blue-700 font-semibold rounded-xl",
                data_uk_toggle="target: #nySkydning")
        ),

        nySkydning(),

        getNavBar(active="Skydninger"),

        # Liste i stedet for tabel på mobil
        Div(
            *[
                Card(cls="p-4 rounded-2xl shadow-md hover:shadow-lg transition")(
                    Div(
                        H3(entry["skydebaner"]["name"], cls="font-bold"),
                        P(str(entry["date"]).replace('T', ' - '), cls="text-sm text-gray-400"),
                        cls="flex justify-between items-center"
                    ),
                    Div(
                        Span(f"{entry['result_hit']} / {entry['result_shots']}",
                            cls="text-lg font-bold"),
                        Span(f"{entry['type']} duer",
                            cls="text-xs bg-blue-500 text-white px-2 py-1 rounded-full"),
                        cls="flex justify-between items-center mt-2"
                    ),
                    A("Se detaljer",
                    href=f"/visSkydning/{entry['id']}",
                    cls="text-blue-500 text-sm mt-3 inline-block")
                )
                for entry in data
            ],
            cls="space-y-4"
        ),

        title="Oversigt"
    )

@app.route("/visSkydning/{skydning_id}")
def visSkydning(skydning_id: int):
    data = getSingleShootingData(skydning_id)
    if not data:
        return Div(
            H1("Fejl"),
            P("Skydning ikke fundet."),
            Button("Tilbage til start", hx_get="/start", hx_swap="outerHTML", hx_trigger="click", hx_target="body"), id="errorPage", style="text-align: center; padding: 50px; width: auto;"
        )
    return Container(
                # Top sektion – stort resultat fokus
                Card(cls="p-6 rounded-3xl shadow-xl text-center bg-gradient-to-br from-blue-600 to-blue-800")(
                    H2(data['skydebaner']['name'], cls="text-2xl font-bold text-white"),
                    P(data['date'], cls="text-blue-100"),
                    Div(
                        H1(f"{data['result_hit']} / {data['result_shots']}", cls="text-5xl font-extrabold text-white mt-4"),
                        P(data['occasion'], cls="text-blue-100 mt-2"),
                        cls="mt-4"
                    )
                ),

                Br(),

                # Type badge
                Div(
                    Span(
                        f"{data['type']} duer",
                        cls="px-4 py-1 rounded-full bg-blue-500 text-white text-sm font-semibold"
                    ),
                    cls="flex justify-center"
                ),

                Br(),

                # Duel stats grid (mobil: 2 kolonner, desktop: 4)
                Grid(
                    Card(cls="p-4 text-center shadow-md rounded-2xl")(
                        P("Venstre", cls="text-sm text-gray-400"),
                        H3(f"{data['venstre']} / {data['venstre_skud']}", cls="text-xl font-bold")
                    ),
                    Card(cls="p-4 text-center shadow-md rounded-2xl")(
                        P("Højre", cls="text-sm text-gray-400"),
                        H3(f"{data['hoejre']} / {data['hoejre_skud']}", cls="text-xl font-bold")
                    ),
                    Card(cls="p-4 text-center shadow-md rounded-2xl")(
                        P("Bag", cls="text-sm text-gray-400"),
                        H3(f"{data['bag']} / {data['bag_skud']}", cls="text-xl font-bold")
                    ),
                    Card(cls="p-4 text-center shadow-md rounded-2xl")(
                        P("Spids", cls="text-sm text-gray-400"),
                        H3(f"{data['spids']} / {data['spids_skud']}", cls="text-xl font-bold")
                    ),
                    cls="grid grid-cols-2 md:grid-cols-4 gap-4"
                ),

                Br(),

                # Vejr sektion
                Card(cls="p-5 rounded-2xl shadow-lg")(
                    H4("Vejrforhold", cls="font-bold text-lg mb-4"),

                    Grid(
                        Div(
                            P("Temperatur", cls="text-xs text-gray-400"),
                            P(f"{data['vejr']['temp']} °C" if data.get("vejr") and data["vejr"].get("temp") is not None else "N/A",
                            cls="font-semibold")
                        ),
                        Div(
                            P("Skydække", cls="text-xs text-gray-400"),
                            P(f"{data['vejr']['skydaekke']} %" if data.get("vejr") and data["vejr"].get("skydaekke") is not None else "N/A",
                            cls="font-semibold")
                        ),
                        Div(
                            P("Vind", cls="text-xs text-gray-400"),
                            P(f"{data['vejr']['vind']} m/s" if data.get("vejr") and data["vejr"].get("vind") is not None else "N/A",
                            cls="font-semibold")
                        ),
                        Div(
                            P("Retning", cls="text-xs text-gray-400"),
                            P(f"{GetWindDirection(data['vejr']['vind_dir'])} ({data['vejr']['vind_dir']}°)"
                            if data.get("vejr") and data["vejr"].get("vind_dir") is not None else "N/A",
                            cls="font-semibold")
                        ),
                        Div(
                            P("Vejr", cls="text-xs text-gray-400"),
                            P(f"{translateWeatherCode(data['vejr']['weather_code'])}" if data.get("vejr") and data["vejr"].get("weather_code") is not None else "N/A",
                            cls="font-semibold")
                        ),
                        cls="grid grid-cols-2 gap-4"
                    )
                ),

                Br(),

                DivRAligned(
                    Button(
                        "← Tilbage",
                        cls=ButtonT.primary,
                        hx_get="/start",
                        hx_swap="outerHTML",
                        hx_target="body"
                    )
                ),

                cls="max-w-3xl mx-auto p-4 space-y-4"
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