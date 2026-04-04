import os
import uuid
import random
from datetime import datetime
import pandas as pd
import math
import streamlit as st
from streamlit_scroll_to_top import scroll_to_here
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

def force_scroll_top():
    components.html(
        """
        <script>
        const selectors = [
          '[data-testid="stAppViewContainer"]',
          'section.main',
          '.main'
        ];

        for (const sel of selectors) {
          const el = window.parent.document.querySelector(sel);
          if (el) {
            el.scrollTo(0, 0);
          }
        }

        window.parent.scrollTo(0, 0);
        </script>
        """,
        height=0,
    )


# Initialize session state with default values
def init_session_state():
    defaults = {
                    "stage": "welcome",
                    "likert_trials": None,
                    "participant_id": None,
                    "pairwise_trials_prepared": None,
                    "profile_saved": False,
                    "likert_saved": False,
                    "pairwise_saved": False,
                    "scroll_to_top_pending": False
                }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# Handle pending scroll to top
def handle_pending_scroll():
    if st.session_state.get("scroll_to_top_pending", False):
        scroll_to_here(0, key=f"scroll_top_{st.session_state.stage}")
        st.session_state.scroll_to_top_pending = False


# Generate a unique participant ID
def generate_participant_id():
    return f"PA{uuid.uuid4().hex[:6].upper()}"

# Get current timestamp
def get_current_timestamp():
    return datetime.now().isoformat(timespec="seconds")

# Ensure output directories exist
def ensure_output_dirs():
    os.makedirs("data/responses", exist_ok=True)

# Generate a seed from a string. Returns an integer.
def seed_from_string(value):
    return abs(hash(value)) % (2**32)


# Load likert trials from Excel file and validate columns. Returns a dataframe with the trials. Throws an error if the columns are missing.
def load_likert_trials(xlsx_path):
    df = pd.read_excel(xlsx_path)
    expected_cols = [
                        "trial_id",
                        "source_clip_id",
                        "audio_path",
                        "performer_type",
                        "split",
                        "notes",
                    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in likert trials file: {missing}")
    return df

# Load pairwise trials from Excel file and validate columns. Returns a dataframe with the trials. Throws an error if the columns are missing.
def load_pairwise_trials(xlsx_path):
    df = pd.read_excel(xlsx_path)
    expected_cols = [
                        "trial_id",
                        "source_clip_id",
                        "baseline_audio_path",
                        "fine_tuned_audio_path",
                        "performer_type",
                        "split",
                        "notes",
                    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in pairwise trials file: {missing}")
    return df

# Shuffle likert trials. Returns a dataframe with the trials shuffled.
# def shuffle_likert_trials(df, seed=None):
#     return df.sample(frac=1, random_state=seed).reset_index(drop=True)

def shuffle_likert_trials(df, seed=None):
    if isinstance(seed, str):
        seed = seed_from_string(seed)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)



# Prepare pairwise trials for a participant. Returns a dataframe with the trials and the labels for the trials.
# def prepare_pairwise_trials_for_participant(df, seed=None):
    # rng = random.Random(seed)
    # rows = []

    # shuffled = df.sample(frac=1, random_state=seed).reset_index(drop=True)


def prepare_pairwise_trials_for_participant(df, seed=None):
    if isinstance(seed, str):
        seed = seed_from_string(seed)

    rng = random.Random(seed)
    rows = []

    shuffled = df.sample(frac=1, random_state=seed).reset_index(drop=True)


    for _, row in shuffled.iterrows():
        baseline_path = row["baseline_audio_path"]
        finetuned_path = row["fine_tuned_audio_path"]

        if rng.choice([True, False]):
            audio_a = baseline_path
            audio_b = finetuned_path
            label_a = "baseline"
            label_b = "finetuned"
        else:
            audio_a = finetuned_path
            audio_b = baseline_path
            label_a = "finetuned"
            label_b = "baseline"

        rows.append(
                    {
                        "trial_id": row["trial_id"],
                        "source_clip_id": row["source_clip_id"],
                        "audio_A_path": audio_a,
                        "audio_B_path": audio_b,
                        "label_A": label_a,
                        "label_B": label_b,
                        "performer_type": row.get("performer_type", ""),
                        "split": row.get("split", ""),
                        "notes": row.get("notes", ""),
                    }
                )

    return pd.DataFrame(rows)

# Render instructions expander. Shows the instructions for the page.
def render_instructions_expander(page_name):
    if page_name == "welcome":
        title = "Details of the survey"
        with st.expander(title, expanded=True):
            st.markdown(
                            """
                            ### What you will do
                            There are 3 sections in this evaluation survey:
                            - :blue[Profile]: Complete a short profile form
                            - :blue[Rating AI generated clips]: Rate 6 AI generated carnatic musical clips
                            - :blue[Clip A v/s Clip B]: Compare 6 pairs of AI generated music (12 clips) from two different music generation models' 
                            
                            ****:blue[Approximate time to complete the survey:]**** 15 ~ 20 mins

                            ### Note:
                            - Please use headphones if possible.
                            - There are no right or wrong answers.
                            """
                        )

    elif page_name == "profile":
        title = "Why we ask for this information"
        st.subheader(title)
        profile_text = f"""This section collects a few details about your familiarity with Carnatic music to help interpret evaluation results across different listener backgrounds."""
        st.info(profile_text)
        profile_details_text = "What information is collected"
        with st.expander(profile_details_text, expanded=True):
            st.markdown("""
                            - Your name (optional)
                            - Your Phone number (optional)
                            - Your familiarity with Carnatic music\n
                                If yes,
                                - Your level of formal training (if any)
                                - Your self-assessed knowledge level on carnatic nuances
                            - Whether you are using headphones
                            """
                        )
            st.markdown(":blue[****Note on Privacy and Data Usage:****]")
            st.markdown("""
                            - Providing personal information is not mandatory
                            - Any information collected will be used only for research purposes
                            - Personal data, if provided, will be used solely to reach out for clarification or follow-up regarding your responses
                            - Your responses will be anonymized during analysis
                        """
                        )
    elif page_name == "likert":
        title = "Instructions"
        with st.expander(title, expanded=True):
            st.markdown(
                        """
                        ### Task
                        You will rate **6 audio clips**.

                        Each clip is **20 seconds** long:
                        - First 10 seconds is the original concert audio of the musicians.
                        - Next 10 seconds is the AI generated continuation.

                        Please rate each clip considering the following metrics:
                        - :blue[Musicality of the generated continuation:] 
                            - Does it feel like a coherent piece of music rather than random or noisy sounds?
                            - Does the music sound expressive, and well-formed?                     
                        - :blue[Continuity/smoothness of continuation:] 
                            - Focus on the transition between the original audio and the generated continuation. 
                            - How well the generated continuation follows the original audio?
                            - Does it feel like a natural continuation of the original audio?
                            - Is there any abrupt changes or breaks in the continuity?
                        - :blue[Carnatic style authenticity:] 
                            - How well the generated continuation reflects Carnatic music characteristics?
                            - Does it sound like Carnatic music in terms of melody and overall style?
                            - Even if you are not an expert, try to judge whether it resembles traditional Carnatic music rather than generic or Western-style music.

                        ### Rating scale
                        - 1 = Very Poor
                        - 2 = Poor
                        - 3 = Average
                        - 4 = Good
                        - 5 = Excellent
                        """
                    )
            # render_metric_descriptions()

    elif page_name == "pairwise":
        title = "Instructions"
        with st.expander(title, expanded=True):
            st.markdown(
                            """
                            ### Task
                            You will evaluate **6 comparison pairs** of audio clips.

                            In each comparison pair:
                            - Clip A and Clip B share the same original source audio.
                            - For both clips:
                                - First 10 seconds is the original concert audio of the musicians.
                                - Next 10 seconds is the AI generated continuation.
                            - Clip A and Clip B are from two different music generation models.
                            - Listen to both clips carefully, and compare the two clips on following aspects:
                                - :blue[Overall Musicality of the generated continuation]:
                                    - Which clip feels more coherent piece of music rather than random or noisy sounds?
                                    - Which clip sounds expressive, and well-formed?                     
                                - :blue[Carnatic Authenticity of the generated continuation]:
                                    - Which clip's generated continuation better reflects Carnatic music characteristics?
                                    - Which clip's generated continuation sounds more like Carnatic music in terms of melody and overall style?
                                    - Even if you are not an expert, try to judge which clip's generated continuation resembles traditional Carnatic music rather than generic or Western-style music.
                                - :blue[Smoothness of generated continuation]:
                                    - Focus on the transition between the original audio and the generated continuation. 
                                    - Which clip has a better continuity/smoothness of the generated music?
                                    - Which clip has a natural continuation of the original music?
                            """
                        )

    elif page_name == "final":
        title = "Thank You"
        st.success(
                        """
                        Your responses have been recorded successfully.\n\n
                        I sincerely appreciate your time and thank you for participating in this evaluation survey of my research capstone.
                        """
                    )


def render_metric_descriptions():
    st.markdown(
                """
                **Musicality**  
                How pleasant and musically meaningful the audio sounds overall.

                **Continuity / Smoothness of continuation**  
                How naturally the generated part follows the original audio.

                **Carnatic style authenticity**  
                How well the continuation reflects Carnatic music characteristics.

                """
            )
                # **Audio quality**  
                # The clarity and technical quality of the sound.


def render_audio_player(audio_path):
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as f:
            st.audio(f.read(), format="audio/wav")
    else:
        st.warning(f"Audio file not found: {audio_path}")


def validate_profile_inputs(participant_name, carnatic_familiarity, formal_training_level, self_rated_knowledge, consent_to_participate, consent_to_contact):
    if not carnatic_familiarity:
        return False, "Please select your familiarity with Carnatic music."
    
    if carnatic_familiarity == "Yes":
        if not formal_training_level:
            return False, "Please select your formal training level."
        if not self_rated_knowledge:
            return False, "Please provide your self-rated knowledge."
    else:
        formal_training_level = None
        self_rated_knowledge = None

    if not consent_to_participate:
        return False, "You must provide consent to participate before continuing."
    if not consent_to_contact:
        return False, "You must provide consent to contact before continuing."

    return True, f"Welcome, {participant_name}!"


def validate_likert_section(trial_ids):
    required_suffixes = [
                            "musicality",
                            "continuity",
                            "authenticity",
                            # "quality",
                        ]
    for trial_id in trial_ids:
        for suffix in required_suffixes:
            key = f"likert_{trial_id}_{suffix}"
            if key not in st.session_state or st.session_state[key] is None:
                return False, f"Please complete all ratings for trial {trial_id}."
    return True, ""


def validate_pairwise_section(trial_ids):
    required_suffixes = [
                            "better_overall",
                            "more_carnatic",
                            "smoother",
                        ]
    for trial_id in trial_ids:
        for suffix in required_suffixes:
            key = f"pairwise_{trial_id}_{suffix}"
            if key not in st.session_state or st.session_state[key] is None:
                return False, f"Please complete all answers for comparison {trial_id}."
    return True, ""


def append_row_to_csv(row_dict, csv_path):
    ensure_output_dirs()
    row_df = pd.DataFrame([row_dict])

    if os.path.exists(csv_path):
        row_df.to_csv(csv_path, mode="a", header=False, index=False)
    else:
        row_df.to_csv(csv_path, mode="w", header=True, index=False)


def save_participant_profile(profile_dict, csv_path):
    append_row_to_csv(profile_dict, csv_path)


def save_likert_responses(response_rows, csv_path):
    ensure_output_dirs()
    df = pd.DataFrame(response_rows)

    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode="a", header=False, index=False)
    else:
        df.to_csv(csv_path, mode="w", header=True, index=False)


def save_pairwise_responses(response_rows, csv_path):
    ensure_output_dirs()
    df = pd.DataFrame(response_rows)

    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode="a", header=False, index=False)
    else:
        df.to_csv(csv_path, mode="w", header=True, index=False)


def build_likert_response_rows(participant_id, trials_df):
    rows = []
    timestamp = get_current_timestamp()

    for idx, row in trials_df.iterrows():
        trial_id = row["trial_id"]

        rows.append(
                    {
                        "participant_id": participant_id,
                        "response_timestamp": timestamp,
                        "trial_id": trial_id,
                        "source_clip_id": row["source_clip_id"],
                        "audio_path": row["audio_path"],
                        "trial_order": idx + 1,
                        "musicality": st.session_state.get(f"likert_{trial_id}_musicality"),
                        "continuity": st.session_state.get(f"likert_{trial_id}_continuity"),
                        "carnatic_authenticity": st.session_state.get(f"likert_{trial_id}_authenticity"),
                        # "audio_quality": st.session_state.get(f"likert_{trial_id}_quality"),
                        "trial_comment": st.session_state.get(f"likert_{trial_id}_comment", ""),
                        "performer_type": row.get("performer_type", ""),
                        "split": row.get("split", ""),
                        "notes": row.get("notes", ""),
                    }
                )
    return rows


def build_pairwise_response_rows(participant_id, trials_df):
    rows = []
    timestamp = get_current_timestamp()

    for idx, row in trials_df.iterrows():
        trial_id = row["trial_id"]

        rows.append(
                    {
                        "participant_id": participant_id,
                        "response_timestamp": timestamp,
                        "trial_id": trial_id,
                        "source_clip_id": row["source_clip_id"],
                        "trial_order": idx + 1,
                        "audio_A_path": row["audio_A_path"],
                        "audio_B_path": row["audio_B_path"],
                        "label_A": row["label_A"],
                        "label_B": row["label_B"],
                        "better_overall": st.session_state.get(f"pairwise_{trial_id}_better_overall"),
                        "more_carnatic": st.session_state.get(f"pairwise_{trial_id}_more_carnatic"),
                        "smoother_continuation": st.session_state.get(f"pairwise_{trial_id}_smoother"),
                        "trial_comment": st.session_state.get(f"pairwise_{trial_id}_comment", ""),
                        "performer_type": row.get("performer_type", ""),
                        "split": row.get("split", ""),
                        "notes": row.get("notes", ""),
                    }
                )
    return rows


# Get Google Sheet client
#Local file
# def get_gsheet_client():
#     scope = [
#                 "https://www.googleapis.com/auth/spreadsheets",
#                 "https://www.googleapis.com/auth/drive",
#             ]

#     credentials = Credentials.from_service_account_file(
#                                                             "secrets/google_service_account.json",
#                                                             scopes=scope,
#                                                         )

#     return gspread.authorize(credentials)

#Streamlit secrets
def get_gsheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
                                                            st.secrets["gcp_service_account"],
                                                            scopes=scope,
                                                        )

    return gspread.authorize(credentials)

# Open a worksheet by name
def get_worksheet(spreadsheet_id, worksheet_name):
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(worksheet_name)


# Clean a value for Google Sheets (Google Sheets append goes through JSON, and JSON does not allow those float values like NaN, inf, or -inf)
def clean_gsheet_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return ""
    return value

# Append one row to a worksheet
def append_row_to_gsheet(row_dict, spreadsheet_id, worksheet_name):
    worksheet = get_worksheet(spreadsheet_id, worksheet_name)

    existing_headers = worksheet.row_values(1)
    row_keys = list(row_dict.keys())

    if not existing_headers:
        worksheet.append_row(row_keys)
        existing_headers = row_keys

    # row_values = [row_dict.get(col, "") for col in existing_headers]
    row_values = [clean_gsheet_value(row_dict.get(col, "")) for col in existing_headers]

    worksheet.append_row(row_values)

#Append many rows
def append_rows_to_gsheet(rows, spreadsheet_id, worksheet_name):
    if not rows:
        return

    worksheet = get_worksheet(spreadsheet_id, worksheet_name)

    existing_headers = worksheet.row_values(1)
    row_keys = list(rows[0].keys())

    if not existing_headers:
        worksheet.append_row(row_keys)
        existing_headers = row_keys

    values = []
    for row_dict in rows:
        # values.append([row_dict.get(col, "") for col in existing_headers])
        values.append([clean_gsheet_value(row_dict.get(col, "")) for col in existing_headers])

    worksheet.append_rows(values)

# Save participant profile to Google Sheet
def save_participant_profile_gsheet(profile_dict, spreadsheet_id):
    append_row_to_gsheet(profile_dict, spreadsheet_id, "participant_profiles")

def save_likert_responses_gsheet(response_rows, spreadsheet_id):
    append_rows_to_gsheet(response_rows, spreadsheet_id, "likert_responses")

def save_pairwise_responses_gsheet(response_rows, spreadsheet_id):
    append_rows_to_gsheet(response_rows, spreadsheet_id, "pairwise_responses")
