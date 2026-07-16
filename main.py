import os
import uuid
import json
import pandas as pd
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

DropDown_Sideduer_default = list(reversed(range(1, 11)))
DropDown_Skud_default = ['10', '11', '12', '13', '14']
        
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

entry, rt = fast_app(secret_key="superhemmeligkey", hdrs=Theme.blue.headers(), dark_mode=True)
app = entry # entry point in vercel  

def AppLayout(*content, title=None):
    return Container(
        Div(
            Style("""
                .htmx-indicator { display: none; }
                .htmx-request .htmx-indicator { display: inline-block; }
            """),
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

def getWindDirectionCategory(degrees):
    if pd.isna(degrees):
        return None
    normalized_degrees = float(degrees) % 360
    return GetWindDirection(normalized_degrees)

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

def getDistinctShoortingYears(userId: int = None):
    if userId is None:
        return []
    try:
        response = supabase.from_("skydning") \
            .select("date") \
            .eq("userId", userId) \
            .execute()
    except Exception as e:
        print(f"Fejl ved hentning af data: {e}")
        return []
    years = set()
    for entry in response.data:
        year = entry["date"].split("-")[0]
        years.add(year)
    return sorted(list(years), reverse=True)

def getShootingData24Duer(userId: int = None):
    if userId is None:
        return []
    try:
        response = supabase.from_("skydning") \
            .select("*, skydebaner(name), vejr(temp, skydaekke, vind, vind_dir, weather_code)") \
            .eq("userId", userId) \
            .eq("type", 24) \
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
    weather_df = df.copy()
    weather_df = weather_df.dropna(subset=["vejr.temp", "vejr.skydaekke", "vejr.vind", "vejr.vind_dir", "vejr.weather_code"], how="all")
    temp_percentages = df.groupby(pd.cut(df["vejr.temp"], bins=5), observed=False).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    cloud_percentages = df.groupby(pd.cut(df["vejr.skydaekke"], bins=5), observed=False).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    wind_speed_percentages = df.groupby(pd.cut(df["vejr.vind"], bins=3), observed=False).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    weather_df["vejr.vind_dir_label"] = weather_df["vejr.vind_dir"].apply(getWindDirectionCategory)
    wind_dir_percentages = weather_df.dropna(subset=["vejr.vind_dir_label"]).groupby("vejr.vind_dir_label", observed=False).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reindex(["N", "NØ", "Ø", "SØ", "S", "SV", "V", "NV"]).dropna(how="all").reset_index()
    weather_code_percentages = df.groupby("vejr.weather_code", observed=False).agg({
        "result_hit": "mean",
        "venstre": "mean",
        "hoejre": "mean",
        "bag": "mean",
        "spids": "mean"
    }).reset_index()
    temp_percentages["vejr.temp"] = temp_percentages["vejr.temp"].apply(lambda x: x.mid.round(2))
    cloud_percentages["vejr.skydaekke"] = cloud_percentages["vejr.skydaekke"].apply(lambda x: x.mid.round(2))
    wind_speed_percentages["vejr.vind"] = wind_speed_percentages["vejr.vind"].apply(lambda x: x.mid.round(2))
    wind_dir_percentages = wind_dir_percentages.rename(columns={"vejr.vind_dir_label": "vejr.vind_dir"})
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

def getPercentages(df, type=40):
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

    def percent_by_shots(frame):
        frame = frame.copy()
        result_shots_safe = frame["result_shots"].replace(0, pd.NA)
        venstre_shots_safe = frame["venstre_skud"].replace(0, pd.NA)
        hoejre_shots_safe = frame["hoejre_skud"].replace(0, pd.NA)
        bag_shots_safe = frame["bag_skud"].replace(0, pd.NA)
        spids_shots_safe = frame["spids_skud"].replace(0, pd.NA)

        frame["result_hit"] = (frame["result_hit"] / result_shots_safe * 100).round(2).fillna(0)
        frame["venstre"] = (frame["venstre"] / venstre_shots_safe * 100).round(2).fillna(0)
        frame["hoejre"] = (frame["hoejre"] / hoejre_shots_safe * 100).round(2).fillna(0)
        frame["bag"] = (frame["bag"] / bag_shots_safe * 100).round(2).fillna(0)
        frame["spids"] = (frame["spids"] / spids_shots_safe * 100).round(2).fillna(0)
        return frame

    occasion_percentages = percent_by_shots(occasion_percentages)
    location_percentages = percent_by_shots(location_percentages)
    normal_percentages = percent_by_shots(normal_percentages)
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
    graph_html = fig.to_html(full_html=False,
                            include_plotlyjs='cdn',
                            config={
                                "displayModeBar": False,
                                "staticPlot": True
                    })

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

    graph_html = fig.to_html(full_html=False,
                            include_plotlyjs='cdn',
                            config={
                                "displayModeBar": False,
                                "staticPlot": True
                    })
    
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

def saveShootingData(place: str, useriD: int, date: str, occation: str, type: int, result_hit: int, result_shot: int, venstre :int, venstre_skud: int, hoejre: int, hoejre_skud: int, bag: int , bag_skud: int, spids: int, spids_skud: int, cell_states: str = "", venstre_cells=None, bag_cells=None, hoejre_cells=None, spids_cells=None):
    skydebaneId, lat, lon = findSkydebaneInfo(place)
    if skydebaneId is None:
        print(f"Skydebane '{place}' ikke fundet i databasen.")
        return False
    temp, cloudCover, wind_speed, wind_direction, weather_code = getweatherData(lat, lon, date) or (None, None, None, None, None)
    payload = {
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
    }
    if cell_states:
        payload["cell_states"] = cell_states
    if venstre_cells is not None:
        payload["venstre_cells"] = venstre_cells
    if bag_cells is not None:
        payload["bag_cells"] = bag_cells
    if hoejre_cells is not None:
        payload["hoejre_cells"] = hoejre_cells
    if spids_cells is not None:
        payload["spids_cells"] = spids_cells
    try:
        response = supabase.table("skydning").insert(payload).execute()
    except Exception as e:
        if cell_states and "cell_states" in payload:
            try:
                payload.pop("cell_states")
                response = supabase.table("skydning").insert(payload).execute()
            except Exception as fallback_error:
                print(f"Fejl ved gemning af data: {fallback_error}")
                return False
        else:
            print(f"Fejl ved gemning af data: {e}")
            return False
    try:
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
    columns = len(sideduer)
    double_columns = {1, 2, 4, 5} if columns == 6 else {1, 2, 4, 5, 7, 8}
    side_rows = [
        ("venstre", "Venstre"),
        ("bag", "Bag"),
        ("hoejre", "Højre"),
        ("spids", "Spids")
    ]

    def row(side_key, label):
        return Tr(
            Th(label, cls="text-left p-1 sm:p-2 align-middle text-xs sm:text-sm w-12 sm:w-24 whitespace-nowrap"),
            *[
                Td(
                    Button(
                        "1",
                        type="button",
                        cls=("duer-cell w-7 h-8 sm:w-full sm:h-10 rounded border text-xs sm:text-lg font-bold " + ("border-blue-500 bg-blue-900/30" if col_idx in double_columns else "border-gray-600")),
                        data_side=side_key,
                        data_is_double="1" if col_idx in double_columns else "0",
                        data_state="1",
                        onclick="cycleDuerCell(this)"
                    ),
                    cls="p-0.5 sm:p-1 text-center align-middle w-7 sm:w-10"
                )
                for col_idx in range(columns)
            ],
            Td(
                Input(type="hidden", name=f"skydning_{side_key}_skud", value=str(columns), id=f"skydning_{side_key}_skud"),
                Input(type="hidden", name=f"skydning_{side_key}", value=str(columns), id=f"skydning_{side_key}")
            )
        )

    return Div(
        Div("Duer", cls="font-semibold text-sm mb-2"),
        Div("Single: 1, 1', 0, 0' | Double (markeret, 2 felter): 1, 0", cls="text-xs text-gray-400"),
        Input(type="hidden", id="skydning_cell_states", name="skydning_cell_states", value=""),
        Div(cls="w-full")(
            Table(cls="table table-sm table-fixed w-full border border-gray-700 rounded-xl")(
                Thead(
                    Tr(
                        Th("Side", cls="text-left p-1 sm:p-2 w-12 sm:w-24 text-xs sm:text-sm"),
                        *[Th(str(i + 1), cls=("text-center p-0.5 sm:p-2 w-7 sm:w-10 text-xs sm:text-sm " + ("text-blue-300" if i in double_columns else ""))) for i in range(columns)]
                    )
                ),
                Tbody(*[row(side_key, label) for side_key, label in side_rows])
            )
        ),
        Div(cls="text-base font-semibold")(
            Span("Score: "),
            Span("0/0", id="skydning_total_score_display")
        ),
        Script("""
            function cycleDuerCell(cell) {
                const current = Number(cell.dataset.state || '1');
                const isDouble = cell.dataset.isDouble === '1';
                const nextState = isDouble ? (current === 1 ? 3 : 1) : (current >= 4 ? 1 : current + 1);
                cell.dataset.state = String(nextState);
                const stateSymbols = {
                    1: '1',
                    2: "1'",
                    3: '0',
                    4: "0'"
                };
                cell.textContent = stateSymbols[nextState];
                updateDuerTotals();
            }

            function updateDuerTotals() {
                const sides = ["venstre", "bag", "hoejre", "spids"];
                let totalHits = 0;
                let totalShots = 0;
                sides.forEach((side) => {
                    const cells = document.querySelectorAll('#duerContainer .duer-cell[data-side="' + side + '"]');
                    let hits = 0;
                    let shots = 0;

                    cells.forEach((cell) => {
                        const state = Number(cell.dataset.state || '1');
                        if (state === 1) {
                            hits += 1;
                            shots += 1;
                        } else if (state === 2) {
                            hits += 1;
                            shots += 2;
                        } else if (state === 3) {
                            shots += 1;
                        } else if (state === 4) {
                            shots += 2;
                        }
                    });

                    const hitHidden = document.getElementById('skydning_' + side);
                    const shotHidden = document.getElementById('skydning_' + side + '_skud');

                    if (hitHidden) hitHidden.value = String(hits);
                    if (shotHidden) shotHidden.value = String(shots);

                    totalHits += hits;
                    totalShots += shots;
                });

                const totalScoreDisplay = document.getElementById('skydning_total_score_display');
                if (totalScoreDisplay) totalScoreDisplay.textContent = String(totalHits) + '/' + String(totalShots);

                const statePayload = sides.map((side) => {
                    const cells = document.querySelectorAll('#duerContainer .duer-cell[data-side="' + side + '"]');
                    return {
                        side: side,
                        entries: Array.from(cells).map((cell) => Number(cell.dataset.state || '1'))
                    };
                });

                const stateInput = document.getElementById('skydning_cell_states');
                if (stateInput) stateInput.value = JSON.stringify(statePayload);
            }
            updateDuerTotals();
        """),
        id="duerContainer",
        cls="space-y-3"
    )

def render_saved_duer_grid(data):
    side_order = ["venstre", "bag", "hoejre", "spids"]

    def parse_entries(raw):
        if raw is None:
            return None
        values = None
        if isinstance(raw, list):
            values = raw
        elif isinstance(raw, str):
            text = raw.strip()
            if not text:
                return None
            try:
                parsed = json.loads(text)
            except Exception:
                return None
            values = parsed if isinstance(parsed, list) else None
        if not isinstance(values, list):
            return None

        normalized = []
        for value in values:
            try:
                state = int(value)
            except Exception:
                state = 1
            if state < 1 or state > 4:
                state = 1
            normalized.append(state)
        return normalized

    side_entries = {
        "venstre": parse_entries(data.get("venstre_cells")),
        "bag": parse_entries(data.get("bag_cells")),
        "hoejre": parse_entries(data.get("hoejre_cells")),
        "spids": parse_entries(data.get("spids_cells"))
    }

    has_any_side_cells = any(entries for entries in side_entries.values())

    if not has_any_side_cells:
        raw_cell_states = data.get("cell_states")
        try:
            parsed_states = json.loads(raw_cell_states) if isinstance(raw_cell_states, str) and raw_cell_states.strip() else raw_cell_states
        except Exception:
            parsed_states = None
        if isinstance(parsed_states, list):
            for side_entry in parsed_states:
                if not isinstance(side_entry, dict):
                    continue
                side = side_entry.get("side")
                if side not in side_entries:
                    continue
                parsed_entries = parse_entries(side_entry.get("entries"))
                if parsed_entries:
                    side_entries[side] = parsed_entries

    if not any(entries for entries in side_entries.values()):
        return None

    lengths = [len(entries) for entries in side_entries.values() if entries]
    columns = max(lengths) if lengths else (6 if int(data.get("type", 40)) == 24 else 10)
    if columns not in (6, 10):
        columns = 6 if int(data.get("type", 40)) == 24 else 10

    double_columns = {1, 2, 4, 5} if columns == 6 else {1, 2, 4, 5, 7, 8}
    state_symbols = {1: "1", 2: "1'", 3: "0", 4: "0'"}

    for side in side_order:
        entries = side_entries.get(side)
        if not entries:
            entries = [1] * columns
        if len(entries) < columns:
            entries = entries + [1] * (columns - len(entries))
        if len(entries) > columns:
            entries = entries[:columns]
        side_entries[side] = entries

    def score_for_entries(entries):
        hits = 0
        shots = 0
        for state in entries:
            if state == 1:
                hits += 1
                shots += 1
            elif state == 2:
                hits += 1
                shots += 2
            elif state == 3:
                shots += 1
            elif state == 4:
                shots += 2
        return hits, shots

    total_hits = 0
    total_shots = 0
    for side in side_order:
        side_hits, side_shots = score_for_entries(side_entries[side])
        total_hits += side_hits
        total_shots += side_shots

    row_labels = {
        "venstre": "Venstre",
        "bag": "Bag",
        "hoejre": "Højre",
        "spids": "Spids"
    }

    def row(side):
        return Tr(
            Th(row_labels[side], cls="text-left p-2 align-middle"),
            *[
                Td(
                    Span(
                        state_symbols[side_entries[side][col_idx]],
                        cls=("inline-flex items-center justify-center w-full h-10 rounded border text-lg font-bold " + ("border-blue-500 bg-blue-900/30" if col_idx in double_columns else "border-gray-600"))
                    ),
                    cls="p-1 text-center align-middle w-10"
                )
                for col_idx in range(columns)
            ]
        )

    return Div(
        Div("Duer", cls="font-semibold text-sm mb-2"),
        Div("Single: 1, 1', 0, 0' | Double (markeret, 2 felter): 1, 0", cls="text-xs text-gray-400"),
        Div(cls="overflow-x-auto")(
            Table(cls="table table-sm table-fixed w-full border border-gray-700 rounded-xl")(
                Thead(
                    Tr(
                        Th("Side", cls="text-left p-2 w-24"),
                        *[Th(str(i + 1), cls=("text-center p-2 w-10 " + ("text-blue-300" if i in double_columns else ""))) for i in range(columns)]
                    )
                ),
                Tbody(*[row(side) for side in side_order])
            )
        ),
        Div(cls="text-base font-semibold")(
            Span("Score: "),
            Span(f"{total_hits}/{total_shots}")
        ),
        cls="space-y-3"
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
        tab("24 duer", "24 duer", "/statistik/24duer"),
        tab("Miss", "Miss", "/statistik/miss"),
        alt=True
    )

def getYearNavBar(years, active_year=None, base_path="/start"):
    items = [
        Li(
            A("Alle", hx_get=base_path, hx_target="body", hx_swap="outerHTML"),
            cls="uk-active" if active_year is None else ""
        )
    ]
    items.extend([
        Li(
            A(str(year), hx_get=f"{base_path}/{year}", hx_target="body", hx_swap="outerHTML"),
            cls="uk-active" if str(active_year) == str(year) else ""
        )
        for year in years
    ])
    return TabContainer(*items, alt=True)

def parse_saved_cell_entries(raw):
    if raw is None:
        return None
    values = None
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except Exception:
            return None
        values = parsed if isinstance(parsed, list) else None
    if not isinstance(values, list):
        return None

    normalized = []
    for value in values:
        try:
            state = int(value)
        except Exception:
            state = 1
        if state < 1 or state > 4:
            state = 1
        normalized.append(state)
    return normalized

def extract_side_entries(record):
    side_entries = {
        "venstre": parse_saved_cell_entries(record.get("venstre_cells")),
        "bag": parse_saved_cell_entries(record.get("bag_cells")),
        "hoejre": parse_saved_cell_entries(record.get("hoejre_cells")),
        "spids": parse_saved_cell_entries(record.get("spids_cells"))
    }

    if not any(entries for entries in side_entries.values()):
        raw_cell_states = record.get("cell_states")
        try:
            parsed_states = json.loads(raw_cell_states) if isinstance(raw_cell_states, str) and raw_cell_states.strip() else raw_cell_states
        except Exception:
            parsed_states = None
        if isinstance(parsed_states, list):
            for side_entry in parsed_states:
                if not isinstance(side_entry, dict):
                    continue
                side = side_entry.get("side")
                if side not in side_entries:
                    continue
                parsed_entries = parse_saved_cell_entries(side_entry.get("entries"))
                if parsed_entries:
                    side_entries[side] = parsed_entries

    lengths = [len(entries) for entries in side_entries.values() if entries]
    if not lengths:
        return None, None

    columns = max(lengths)
    if columns not in (6, 10):
        shoot_type = int(record.get("type", 40)) if str(record.get("type", "40")) in ("24", "40") else 40
        columns = 6 if shoot_type == 24 else 10

    for side in side_entries:
        entries = side_entries[side] or [1] * columns
        if len(entries) < columns:
            entries = entries + [1] * (columns - len(entries))
        if len(entries) > columns:
            entries = entries[:columns]
        side_entries[side] = entries

    return side_entries, columns

def getMissAnalysis(data):
    side_order = ["venstre", "bag", "hoejre", "spids"]
    side_labels = {
        "venstre": "Venstre",
        "bag": "Bag",
        "hoejre": "Højre",
        "spids": "Spids"
    }
    misses = {3, 4}
    extra_shot_states = {2, 4}
    singles = {}
    problem_cells = {}

    sorted_data = sorted(data or [], key=lambda entry: entry.get("date", ""))
    for entry in sorted_data:
        side_entries, columns = extract_side_entries(entry)
        if not side_entries or columns not in (6, 10):
            continue

        double_columns = {1, 2, 4, 5} if columns == 6 else {1, 2, 4, 5, 7, 8}
        single_columns = [idx for idx in range(columns) if idx not in double_columns]

        sorted_double_cols = sorted(double_columns)
        double_pairs = []
        idx = 0
        while idx < len(sorted_double_cols) - 1:
            left = sorted_double_cols[idx]
            right = sorted_double_cols[idx + 1]
            if right == left + 1:
                double_pairs.append((left, right))
                idx += 2
            else:
                idx += 1

        for side in side_order:
            entries = side_entries[side]

            for col_idx, state in enumerate(entries):
                key = (side, col_idx + 1)
                if key not in problem_cells:
                    problem_cells[key] = {
                        "side": side,
                        "side_label": side_labels[side],
                        "col_start": col_idx + 1,
                        "col_end": None,
                        "columns": columns,
                        "misses": 0,
                        "attempts": 0
                    }
                problem_cells[key]["columns"] = max(problem_cells[key]["columns"], columns)
                problem_cells[key]["attempts"] += 1
                if state in misses:
                    problem_cells[key]["misses"] += 1

            for col_idx in single_columns:
                key = (side, col_idx + 1)
                if key not in singles:
                    singles[key] = {
                        "side": side,
                        "side_label": side_labels[side],
                        "col_start": col_idx + 1,
                        "col_end": None,
                        "columns": columns,
                        "misses": 0,
                        "extra_shots": 0,
                        "attempts": 0
                    }
                singles[key]["columns"] = max(singles[key]["columns"], columns)
                singles[key]["attempts"] += 1
                if entries[col_idx] in misses:
                    singles[key]["misses"] += 1
                if entries[col_idx] in extra_shot_states:
                    singles[key]["extra_shots"] += 1

    singles_rows = []
    for row in singles.values():
        attempts = row["attempts"]
        misses_count = row["misses"]
        extra_shots_count = row["extra_shots"]
        miss_rate = round((misses_count / attempts) * 100, 2) if attempts else 0
        extra_shot_rate = round((extra_shots_count / attempts) * 100, 2) if attempts else 0
        singles_rows.append({
            "side": row["side"],
            "side_label": row["side_label"],
            "col_start": row["col_start"],
            "col_end": row["col_end"],
            "columns": row["columns"],
            "miss_rate": miss_rate,
            "misses": misses_count,
            "extra_shot_rate": extra_shot_rate,
            "extra_shots": extra_shots_count,
            "attempts": attempts
        })

    problem_rows = []
    for row in problem_cells.values():
        attempts = row["attempts"]
        misses_count = row["misses"]
        miss_rate = round((misses_count / attempts) * 100, 2) if attempts else 0
        problem_rows.append({
            "side": row["side"],
            "side_label": row["side_label"],
            "col_start": row["col_start"],
            "col_end": row["col_end"],
            "columns": row["columns"],
            "miss_rate": miss_rate,
            "misses": misses_count,
            "attempts": attempts
        })

    singles_rows = sorted(singles_rows, key=lambda row: (row["miss_rate"], row["misses"], row["attempts"]), reverse=True)
    extra_singles_rows = sorted(singles_rows, key=lambda row: (row["extra_shot_rate"], row["extra_shots"], row["attempts"]), reverse=True)
    problem_rows = sorted(problem_rows, key=lambda row: (row["miss_rate"], row["misses"], row["attempts"]), reverse=True)

    return {
        "singles": singles_rows,
        "problem_cells": problem_rows,
        "extra_singles": extra_singles_rows
    }

def renderMissPatternRow(row):
    columns = int(row.get("columns", 10))
    columns = 6 if columns == 6 else 10
    double_columns = {1, 2, 4, 5} if columns == 6 else {1, 2, 4, 5, 7, 8}
    highlight_columns = {int(row.get("col_start", 1)) - 1}
    col_end = row.get("col_end")
    if col_end is not None:
        highlight_columns.add(int(col_end) - 1)

    return Div(
        Span(row.get("side_label", ""), cls="inline-block w-16 text-sm font-semibold"),
        Div(
            *[
                Span(
                    "",
                    cls=(
                        "inline-block w-7 h-7 rounded border "
                        + ("border-red-300 bg-red-600" if col_idx in highlight_columns else ("border-green-200" if col_idx in double_columns else "border-green-500"))
                    )
                )
                for col_idx in range(columns)
            ],
            cls="inline-flex gap-1"
        ),
        cls="flex items-center gap-3"
    )

def createMissProblemTable(rows):
    if not rows:
        return Div(P("Ingen data", cls="text-sm text-gray-400"))

    return Table(cls="border-collapse border border-gray-100 table-auto w-full")(
        Thead(
            Tr(
                Th("Duer", cls="text-left border text-bold"),
                Th("Miss %", cls="text-left border text-bold"),
                Th("Misses", cls="text-left border text-bold"),
                Th("Forsøg", cls="text-left border text-bold")
            )
        ),
        Tbody(
            *[
                Tr(
                    Td(renderMissPatternRow(row), cls="text-left border"),
                    Td(f"{row['miss_rate']}%", cls="text-left border"),
                    Td(str(row["misses"]), cls="text-left border"),
                    Td(str(row["attempts"]), cls="text-left border")
                )
                for row in rows
            ]
        )
    )

def createExtraShotProblemTable(rows):
    if not rows:
        return Div(P("Ingen data", cls="text-sm text-gray-400"))

    return Table(cls="border-collapse border border-gray-100 table-auto w-full")(
        Thead(
            Tr(
                Th("Duer", cls="text-left border text-bold"),
                Th("Ekstra skud %", cls="text-left border text-bold"),
                Th("Ekstra skud", cls="text-left border text-bold"),
                Th("Forsøg", cls="text-left border text-bold")
            )
        ),
        Tbody(
            *[
                Tr(
                    Td(renderMissPatternRow(row), cls="text-left border"),
                    Td(f"{row['extra_shot_rate']}%", cls="text-left border"),
                    Td(str(row["extra_shots"]), cls="text-left border"),
                    Td(str(row["attempts"]), cls="text-left border")
                )
                for row in rows
            ]
        )
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
        sideduer = list(reversed(range(1, 11)))
        skud = ['10', '11', '12', '13', '14']
    else:
        sideduer = list(reversed(range(1, 7)))
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

def getDataframeFromData(data, filter_type=40):
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
    
    df = df[df['type'] == filter_type]
    return df
 
@app.route("/statistik/24duer")
@app.route("/statistik/24duer/{year}")
def statistik24duer(session, year: str = None):
    userId = session.get(SESSION_TOKEN)
    print(f"User ID for statistik/24duer: {userId}")
    years = getDistinctShoortingYears(userId=userId)
    data = getShootingData24Duer(userId=userId)
    if year is not None:
        selected_year = str(year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]
    else:
        selected_year = None
    df = getDataframeFromData(data, filter_type=24)

    averages_24duer = getAverages(df)

    resultHeaders = ["Ramte", "Skud", "Venstre", "Venstre skud", "Højre", "Højre skud", "Bag", "Bag skud", "Spids", "Spids skud"]
    resultValueKeys = ["result_hit", "result_shots", "venstre", "venstre_skud", "hoejre", "hoejre_skud", "bag", "bag_skud", "spids", "spids_skud"]
 
    return AppLayout(
            getNavBar(active="Statistik"),
            Br(),
            getStatsNavBar(active="24 duer"),
            getYearNavBar(years, active_year=selected_year, base_path="/statistik/24duer"),
            Br(),
            Div("Resultater samlet", cls="divider text-2xl font-bold"),
            Card("Gennemsnit samlet", cls="font-bold text-center mb-2")(
                createStatsList(resultHeaders, pd.DataFrame([averages_24duer["normal_averages"]]), resultValueKeys)
            ),
            title="Statistik"
        )

@app.route("/statistik/anledning")
@app.route("/statistik/anledning/{year}")
def statistikAnledning(session, year: str = None):
    userId = session.get(SESSION_TOKEN)
    years = getDistinctShoortingYears(userId=userId)
    data = getShootingData(userId=userId)
    if year is not None:
        selected_year = str(year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]
    else:
        selected_year = None
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
            getYearNavBar(years, active_year=selected_year, base_path="/statistik/anledning"),
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
@app.route("/statistik/sted/{year}")
def statistikSted(session, year: str = None):
    userId = session.get(SESSION_TOKEN)
    years = getDistinctShoortingYears(userId=userId)
    data = getShootingData(userId=userId)
    if year is not None:
        selected_year = str(year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]
    else:
        selected_year = None
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
            getYearNavBar(years, active_year=selected_year, base_path="/statistik/sted"),
            Br(),
            Div("Resultater per sted", cls="divider text-2xl font-bold"),
            Card("Gennemsnit per sted", cls="font-bold text-center mb-2")(
                createStatsList(resultHeaders, pd.DataFrame(averages["location_averages"]), resultValueKeys, label_key="skydebaner.name")
            ),
            Card("Procenter per sted", cls="font-bold text-center")(
                createStatsList(percentageHeaders, pd.DataFrame(percetages["location_percentages"]), percentageValueKeys, label_key="skydebaner.name")
            ),
            title="Statistik"
        )
 
@app.route("/statistik/vejr")
@app.route("/statistik/vejr/{year}")
def statistikVejr(session, year: str = None):
    userId = session.get(SESSION_TOKEN)
    years = getDistinctShoortingYears(userId=userId)
    data = getShootingData(userId=userId)
    if year is not None:
        selected_year = str(year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]
    else:
        selected_year = None
    df = getDataframeFromData(data)

    weatherDataPercentages = getPercentagesByWeather(df)

    return AppLayout(

            getNavBar(active="Statistik"),
            Br(),
            getStatsNavBar(active="Vejr"),
            getYearNavBar(years, active_year=selected_year, base_path="/statistik/vejr"),
            Br(),
            
            Titled("Vejrstatistik for samlede resultater",
                   createStatsGraph(weatherDataPercentages["temp_percentages"], "Samlet resultater baseret på temperatur", "Temperatur (°C)", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["cloud_percentages"], "Samlet resultater baseret på sky-dække", "Sky-dække (%)", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["wind_speed_percentages"], "Samlet resultater baseret på vindhastighed", "Vindhastighed (m/s)", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=False),
                   createStatsGraph(weatherDataPercentages["wind_dir_percentages"], "Samlet resultater baseret på vindretning", "Vindretning", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=True),
                   createStatsGraph(weatherDataPercentages["weather_code_percentages"], "Samlet resultater baseret på vejr", "Vejr", "Gennemsnitligt antal ramte duer", Total=True, BarPlot=True),cls="mt-10"),
            title="Statistik"
        )

@app.route("/statistik/miss")
@app.route("/statistik/miss/{year}")
def statistikMiss(session, year: str = None):
    userId = session.get(SESSION_TOKEN)
    years = getDistinctShoortingYears(userId=userId)
    data = getShootingData(userId=userId)
    if year is not None:
        selected_year = str(year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]
    else:
        selected_year = None

    miss_data = getMissAnalysis(data)
    troublesome_rows = [row for row in miss_data["problem_cells"] if row["misses"] > 0][:5]
    extra_singles_rows = [row for row in miss_data["extra_singles"] if row["extra_shots"] > 0][:5]

    return AppLayout(
            getNavBar(active="Statistik"),
            Br(),
            getStatsNavBar(active="Miss"),
            getYearNavBar(years, active_year=selected_year, base_path="/statistik/miss"),
            Br(),
            Div("Mest problematiske duer", cls="divider text-2xl font-bold"),
            Card("Top 5", cls="font-bold text-center mb-2")(
                createMissProblemTable(troublesome_rows)
            ),
            Div("Enkeltduer med flest ekstra skud", cls="divider text-2xl font-bold"),
            Card("Top 5", cls="font-bold text-center mb-2")(
                createExtraShotProblemTable(extra_singles_rows)
            ),
            title="Statistik"
        )
    
@app.route("/statistik")
@app.route("/statistik/{year}")
def statistik(session, year: str = None):
    userId = session.get(SESSION_TOKEN)
    years = getDistinctShoortingYears(userId=userId)
    data = getShootingData(userId=userId)
    if year is not None:
        selected_year = str(year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]
    else:
        selected_year = None
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
            getYearNavBar(years, active_year=selected_year, base_path="/statistik"),
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


def renderStartPage(session, selected_year=None):
    userId = session.get(SESSION_TOKEN)
    data = getShootingData(userId=userId)
    years = getDistinctShoortingYears(userId=userId)
    if selected_year is not None:
        selected_year = str(selected_year)
        data = [entry for entry in data if str(entry.get("date", "")).startswith(f"{selected_year}-")]

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
        getYearNavBar(years, active_year=selected_year, base_path="/start"),

        # Liste i stedet for tabel på mobil
        Div(
            *[
                Card(cls="p-4 rounded-2xl shadow-md hover:shadow-lg transition")(
                    Div(
                        H3(entry["skydebaner"]["name"], cls="font-bold"),
                        P(entry["date"], cls="text-sm text-gray-400"),
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

@app.route("/start")
def startPage(session):
    userId = session.get(SESSION_TOKEN)
    years = getDistinctShoortingYears(userId=userId)
    current_year = str(pd.Timestamp.now().year)
    return renderStartPage(session, selected_year=current_year if current_year in years else None)

@app.route("/start/{year}")
def startPageByYear(session, year: str):
    return renderStartPage(session, selected_year=year)

@app.route("/visSkydning/{skydning_id}")
def visSkydning(skydning_id: int):
    data = getSingleShootingData(skydning_id)
    if not data:
        return Div(
            H1("Fejl"),
            P("Skydning ikke fundet."),
            Button("Tilbage til start", hx_get="/start", hx_swap="outerHTML", hx_trigger="click", hx_target="body"), id="errorPage", style="text-align: center; padding: 50px; width: auto;"
        )
    saved_duer_grid = render_saved_duer_grid(data)
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

                saved_duer_grid if saved_duer_grid else Grid(
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

                Div(
                    cls="flex flex-col md:flex-row justify-between space-y-2 md:space-y-0 md:space-x-2"
                )(
                    Button(
                        "← Tilbage",
                        cls=ButtonT.primary,
                        hx_get="/start",
                        hx_swap="outerHTML",
                        hx_target="body"
                    ),
                    Button(
                        "Slet skydning",
                        cls=ButtonT.secondary,
                        hx_get=f"/sletSkydning/{data['id']}",
                        hx_swap="outerHTML",
                        hx_target="body",
                        hx_trigger="click",
                    )
                ),

                cls="max-w-3xl mx-auto p-4 space-y-4"
            )                
    

def nySkydning():
    return Modal(
        Div(cls='p-6 max-w-4xl')(
            ModalTitle("Opret ny skydning", cls="mb-6 text-2xl font-bold text-center"),
            Form(cls='space-y-6', hx_post="/gemSkydning", hx_swap="outerHTML")(
                LabelSelect(*Options(*[str(skydebane["name"]) for skydebane in skydebaner]), label="Sted", name="skydning_sted"),
                LabelSelect(
                    *Options(*[str(i) for i in getAnledninger()], selected_idx=1, disabled_idxs={0}), label="Anledning", name="skydning_occation"
                ),
                LabelInput(label="Dato", name="skydning_dato", type="datetime-local"),
                Div(cls="space-y-2")(
                    FormLabel("Runde"),
                    DivLAligned(
                        Radio(name="skydning_type", value="40", checked=True, hx_get="/opdaterSkydningType/40", hx_target="#duerContainer", hx_trigger="change")("40"),
                        Radio(name="skydning_type", value="24", hx_get="/opdaterSkydningType/24", hx_target="#duerContainer", hx_trigger="change")("24")
                    )
                ),
                build_duer_grid(DropDown_Sideduer_default, DropDown_Skud_default),
                DivRAligned(
                    ModalCloseButton("Anuller", cls=ButtonT.ghost),
                    Button(
                        "Gem skydning",
                        Span(id="gemSkydningSpinner", cls="htmx-indicator inline-block h-4 w-4 ml-2 animate-spin rounded-full border-2 border-white border-t-transparent align-middle"),
                        cls=ButtonT.primary,
                        type="submit",
                        hx_post="/gemSkydning",
                        hx_swap="outerHTML"
                    ), cls='space-x-2'
                )
            )
        ), id="nySkydning", open=False
    )

@app.route("/gemSkydning", methods=["POST"])
def gemSkydning(session, skydning_sted: str, skydning_dato: str, skydning_occation: str, skydning_type: str = "40", skydning_cell_states: str = ""):
    userId = session.get(SESSION_TOKEN)
    side_hits = {"venstre": 0, "hoejre": 0, "bag": 0, "spids": 0}
    side_shots = {"venstre": 0, "hoejre": 0, "bag": 0, "spids": 0}
    side_cells = {"venstre": None, "hoejre": None, "bag": None, "spids": None}

    normalized_cell_states = ""
    derived_round_size = None
    if skydning_cell_states:
        try:
            parsed_states = json.loads(skydning_cell_states)
            normalized_cell_states = json.dumps(parsed_states, separators=(",", ":"))
            if isinstance(parsed_states, list):
                extracted_round_sizes = []
                extracted_hits = {}
                extracted_shots = {}

                for side_entry in parsed_states:
                    if not isinstance(side_entry, dict):
                        continue
                    side = side_entry.get("side")
                    entries = side_entry.get("entries")
                    if side not in side_hits or not isinstance(entries, list):
                        continue

                    hits = 0
                    shots = 0
                    for raw_state in entries:
                        state = int(raw_state)
                        if state == 1:
                            hits += 1
                            shots += 1
                        elif state == 2:
                            hits += 1
                            shots += 2
                        elif state == 3:
                            shots += 1
                        elif state == 4:
                            shots += 2

                    extracted_hits[side] = hits
                    extracted_shots[side] = shots
                    side_cells[side] = [int(raw_state) for raw_state in entries]
                    extracted_round_sizes.append(len(entries))

                if len(extracted_hits) == 4:
                    side_hits.update(extracted_hits)
                    side_shots.update(extracted_shots)
                    if len(set(extracted_round_sizes)) == 1 and extracted_round_sizes[0] in (6, 10):
                        derived_round_size = extracted_round_sizes[0]
        except Exception:
            normalized_cell_states = ""

    if not normalized_cell_states or sum(side_shots.values()) == 0:
        return Modal(
            Div(cls='p-6')(
                ModalTitle("Fejl", cls="mb-4 text-2xl font-bold text-center"),
                Br(),
                P("Celle-data mangler eller er ugyldig. Prøv at udfylde skydningen igen.", cls="text-center"),
                Br(),
                DivRAligned(
                    ModalCloseButton("Luk", cls=ButtonT.ghost),
                    Button("Tilbage til start", cls=ButtonT.primary, hx_get="/start", hx_swap="outerHTML"), cls='space-x-2'
                )
            ), id="errorModal", open=True
        )

    skydning_venstre = side_hits["venstre"]
    skydning_hoejre = side_hits["hoejre"]
    skydning_bag = side_hits["bag"]
    skydning_spids = side_hits["spids"]
    skydning_venstre_skud = side_shots["venstre"]
    skydning_hoejre_skud = side_shots["hoejre"]
    skydning_bag_skud = side_shots["bag"]
    skydning_spids_skud = side_shots["spids"]

    skydning_result_hit = skydning_venstre + skydning_hoejre + skydning_bag + skydning_spids
    skydning_result_shots = skydning_venstre_skud + skydning_hoejre_skud + skydning_bag_skud + skydning_spids_skud
    if derived_round_size == 10:
        skydning_type = 40
    elif derived_round_size == 6:
        skydning_type = 24
    else:
        skydning_type = int(skydning_type) if str(skydning_type) in ("24", "40") else (40 if skydning_result_hit > 24 else 24)

    saved = saveShootingData(skydning_sted, userId, skydning_dato, skydning_occation, int(skydning_type), skydning_result_hit, skydning_result_shots,
                              skydning_venstre, skydning_venstre_skud, skydning_hoejre, skydning_hoejre_skud, skydning_bag, skydning_bag_skud, skydning_spids, skydning_spids_skud, normalized_cell_states,
                              venstre_cells=side_cells["venstre"], bag_cells=side_cells["bag"], hoejre_cells=side_cells["hoejre"], spids_cells=side_cells["spids"])
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