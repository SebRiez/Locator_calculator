# creted by Sebastian Riezler
# c 2025

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import os

# === Funktionen ===

def tc_to_frames(tc_str, fps=25):
    h, m, s, f = map(int, tc_str.split(":"))
    return ((h * 3600 + m * 60 + s) * fps + f)

def frames_to_tc(total_frames, fps=25):
    h = total_frames // (3600 * fps)
    m = (total_frames // (60 * fps)) % 60
    s = (total_frames // fps) % 60
    f = total_frames % fps
    return f"{h:02}:{m:02}:{s:02}:{f:02}"

def parse_edl_and_compute_locators(edl_lines, fps=25):
    events = []
    current_event = None
    collecting_locators = False

    event_regex = re.compile(
        r"^(?P<event>\d{6})\s+(?P<clip>\S+)\s+\S+\s+\S+\s+(?P<src_in>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<src_out>\d{2}:\d{2}:\d{2}:\d{2})"
    )

    for line in edl_lines:
        match = event_regex.match(line)
        if match:
            current_event = {
                "event": match.group("event"),
                "src_in_master": match.group("src_in"),
                "locators": []
            }
            events.append(current_event)
            collecting_locators = False
        elif line.strip().startswith("*FROM CLIP NAME:") and current_event:
            collecting_locators = True
        elif "*LOC:" in line and collecting_locators and current_event:
            tc_match = re.search(r"\*LOC:\s+(\d{2}:\d{2}:\d{2}:\d{2})", line)
            if tc_match:
                current_event["locators"].append(tc_match.group(1))
        elif line.strip() == "":
            collecting_locators = False

    # Berechnung
    results = []
    for event in events:
        base_src_in = tc_to_frames(event["src_in_master"], fps)
        base_virtual = tc_to_frames("01:00:00:00", fps)
        for loc_tc in event["locators"]:
            offset = tc_to_frames(loc_tc, fps)
            final_tc = frames_to_tc(base_src_in + (offset - base_virtual), fps)
            results.append({
                "Event": event["event"],
                "Master SRC IN": event["src_in_master"],
                "Locator TC": loc_tc,
                "Computed Master TC": final_tc
            })

    return pd.DataFrame(results)

# === Streamlit UI ===

st.title("Locator Timecode Calculator (pour le general)")

uploaded_file = st.file_uploader("Lade deine EDL-Datei hoch", type=["edl", "txt"])

if uploaded_file:
    edl_lines = uploaded_file.read().decode("utf-8").splitlines()
    fps = st.selectbox("Framerate (fps)", [24, 25, 30], index=1)
    df = parse_edl_and_compute_locators(edl_lines, fps=fps)

    if not df.empty:
        st.success("Locator-Zeitcodes erfolgreich berechnet!")
        st.dataframe(df)

        # Dateiname automatisch erzeugen
        original_name = os.path.splitext(uploaded_file.name)[0]
        date_str = datetime.now().strftime("%y%m%d")
        filename = f"{original_name}_processed_{date_str}.csv"

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("CSV herunterladen", csv, filename, "text/csv")
    else:
        st.warning("Keine gültigen LOC-Einträge gefunden.")
