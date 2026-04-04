import streamlit as st

from app_utils import *

LIKERT_TRIALS_XLSX = "data/likert_trials.xlsx"
PAIRWISE_TRIALS_XLSX = "data/pairwise_trials.xlsx"

PARTICIPANT_PROFILES_CSV = "data/responses/participant_profiles.csv"
LIKERT_RESPONSES_CSV = "data/responses/likert_responses.csv"
PAIRWISE_RESPONSES_CSV = "data/responses/pairwise_responses.csv"

USE_GOOGLE_SHEETS = True
GOOGLE_SHEET_NAME = "Carnatic Music Evaluation Responses"
GOOGLE_SPREADSHEET_ID = st.secrets["app"]["google_spreadsheet_id"]
# It is the id between /d/ and /edit


def show_welcome_page():
    st.title("Evalation of Carnatic Music Generation")
    st.caption("A survey to evaluate the perceptual musical quality and stylistic authenticity of AI-generated Carnatic music continuations.")
    intro_text = f'''**Thank you for your consent to participate in this evaluation survey.**\n\nThis survey is a part of my Master’s research project focused on improving AI-based music generation for non-western musical traditions of cultural significance.\n\nMost of the existing music generation models are pre-dominantly trained on Western music data, which can limit their ability to accurately represent other rich musical traditions such as Carnatic music. As part of this research capstone, I have fine-tuned an existing music generation model to better adapt to the Carnatic music domain, with the goal of improving the model’s ability to generate musically coherent and stylistically accurate continuations.\n\n ***In this evaluation, you will listen to a set of authentic and AI generated Carnatic audio clips and provide feedback on aspects such as musical quality, continuity, and stylistic authenticity of AI generated continuations. Your responses will help assess how well the model has adapted to the Carnatic music style.***'''
    
    st.success(intro_text)

    render_instructions_expander("welcome")

    if st.button("Start Survey", type="primary"):
        if st.session_state.participant_id is None:
            st.session_state.participant_id = generate_participant_id()
        st.session_state.stage = "profile"
        st.rerun()


def show_profile_page():
    st.title("Participant Profile")
    render_instructions_expander("profile")

    participant_name = st.text_input("Your name (optional)", key="profile_name")
    participant_phone_number = st.number_input("Your phone number (optional)", min_value = 0, max_value = 9999999999, value = None, key="profile_phone_number")

    carnatic_familiarity = st.radio(
                                        "Are you familiar with Carnatic music?*",
                                        options=["Yes", "No"],
                                        index=None,
                                        key="profile_carnatic_familiarity",
                                        horizontal=True,
                                    )
    if carnatic_familiarity == "Yes":
        formal_training_level = st.selectbox(
                                                "What is your formal training level in Carnatic music?*",
                                                options=["None", "Beginner", "Intermediate", "Advanced", "Professional",""],
                                                index=5,
                                                key="profile_training_level"
                                            )

        self_rated_knowledge = st.radio(
                                            "How would you rate your Carnatic music knowledge on its nuances?*",
                                            options=[1, 2, 3, 4, 5],
                                            index=None,
                                            key="profile_self_rated_knowledge",
                                            horizontal=True,
                                        )
    else:
        formal_training_level = None
        self_rated_knowledge = None

    uses_headphones = st.radio(
                                "Are you using headphones or earphones?",
                                options=["Yes", "No"],
                                index=None,
                                key="profile_uses_headphones",
                                horizontal=True,
                            )

    comments = st.text_area(
                            "Any additional information you would like me to know before starting",
                            key="profile_comments"
                        )

    consent_to_participate = st.checkbox(
                                            "I have read the study information and consent to participate in this research evaluation.",
                                            key="profile_consent_to_participate",
                                        )

    consent_to_contact = st.checkbox(
                                        "I agree that the researcher may contact me if clarification is needed about my responses.",
                                        key="profile_consent_to_contact",
                                   )

    if st.button("Next", type="primary"):
        is_valid, msg = validate_profile_inputs(
                                                    participant_name,
                                                    carnatic_familiarity,
                                                    formal_training_level,
                                                    self_rated_knowledge,
                                                    consent_to_participate,
                                                    consent_to_contact,
                                                )

        if not is_valid:
            st.error(msg)
            return

        if not st.session_state.profile_saved:
            profile_row = {
                            "participant_id": st.session_state.participant_id,
                            "submitted_at": get_current_timestamp(),
                            "participant_name": participant_name,
                            "participant_phone_number": participant_phone_number,
                            "carnatic_familiarity": carnatic_familiarity,
                            "formal_training_level": formal_training_level,
                            "self_rated_knowledge": self_rated_knowledge,
                            "uses_headphones": uses_headphones,
                            "comments": comments,
                            "consent_to_participate": consent_to_participate,
                            "consent_to_contact": consent_to_contact,
                        }
            if USE_GOOGLE_SHEETS:
                # save_participant_profile_gsheet(profile_row, GOOGLE_SHEET_NAME)
                save_participant_profile_gsheet(profile_row, GOOGLE_SPREADSHEET_ID)
            else:
                save_participant_profile(profile_row, PARTICIPANT_PROFILES_CSV)
            # save_participant_profile(profile_row, PARTICIPANT_PROFILES_CSV)
            # save_participant_profile_gsheet(profile_row, GOOGLE_SHEET_NAME)
            st.session_state.profile_saved = True

        if st.session_state.likert_trials is None:
            likert_df = load_likert_trials(LIKERT_TRIALS_XLSX)
            st.session_state.likert_trials = shuffle_likert_trials(
                                                                    likert_df,
                                                                    seed=st.session_state.participant_id,
                                                                    )

        if st.session_state.pairwise_trials_prepared is None:
            pairwise_df = load_pairwise_trials(PAIRWISE_TRIALS_XLSX)
            st.session_state.pairwise_trials_prepared = prepare_pairwise_trials_for_participant(
                                                                                                pairwise_df,
                                                                                                seed=st.session_state.participant_id,
                                                                                                )
        st.session_state.stage = "likert"
        st.rerun()


def show_likert_page():
    st.title("Rating AI generated clips")
    render_instructions_expander("likert")

    likert_df = st.session_state.likert_trials

    if likert_df is None or likert_df.empty:
        st.error("Data not loaded. Please contact the person who invited you to this survey.")
        return

    for idx, row in likert_df.iterrows():
        trial_id = row["trial_id"]
        expander_title = f"Trial {idx + 1} of {len(likert_df)} — {trial_id}"

        with st.expander(expander_title, expanded=True):
            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.markdown("**Audio Clip**")
                render_audio_player(row["audio_path"])
                
                audio_details = f"First 10 seconds is the original concert audio of the musicians, and the next 10 seconds is the AI generated continuation from the fine-tuned model."
                st.caption(audio_details)

                rating_instructions = f"""
                                        **Rating scale:**
                                        - 1 = Very Poor
                                        - 2 = Poor
                                        - 3 = Average
                                        - 4 = Good
                                        - 5 = Excellent
                                        """
                st.info(rating_instructions)
                
            with right_col:
                st.markdown("**Ratings**")
                st.radio(
                            "Musicality of the generated continuation:",
                            options=[1, 2, 3, 4, 5],
                            index=None,
                            key=f"likert_{trial_id}_musicality",
                            horizontal=True,
                        )
                st.radio(
                            "Continuity / Smoothness of continuation",
                            options=[1, 2, 3, 4, 5],
                            index=None,
                            key=f"likert_{trial_id}_continuity",
                            horizontal=True,
                        )
                st.radio(
                            "Carnatic style authenticity",
                            options=[1, 2, 3, 4, 5],
                            index=None,
                            key=f"likert_{trial_id}_authenticity",
                            horizontal=True,
                        )
                # st.radio(
                #             "Audio quality",
                #             options=[1, 2, 3, 4, 5],
                #             index=None,
                #             key=f"likert_{trial_id}_quality",
                #             horizontal=True,
                #         )
                st.text_area(
                                "Other Feedback (if any):",
                                key=f"likert_{trial_id}_comment",
                                placeholder="Any other feedback on the generated continuation",
                            )

    if st.button("Submit Likert Section", type="primary"):
        trial_ids = likert_df["trial_id"].tolist()
        is_valid, msg = validate_likert_section(trial_ids)

        if not is_valid:
            st.error(msg)
            return

        if not st.session_state.likert_saved:
            rows = build_likert_response_rows(
                                                st.session_state.participant_id,
                                                likert_df,
                                            )

            if USE_GOOGLE_SHEETS:
                save_likert_responses_gsheet(rows, GOOGLE_SPREADSHEET_ID)
            else:
                save_likert_responses(rows, LIKERT_RESPONSES_CSV)
                                            
            # save_likert_responses(rows, LIKERT_RESPONSES_CSV)
            # save_likert_responses_gsheet(rows, GOOGLE_SHEET_NAME)
            st.session_state.likert_saved = True

        st.session_state.stage = "pairwise"
        st.rerun()


def show_pairwise_page():
    st.title("Baseline v/s Fine-tuned clips")
    render_instructions_expander("pairwise")

    pairwise_df = st.session_state.pairwise_trials_prepared

    if pairwise_df is None or pairwise_df.empty:
        st.error("Pairwise trials not loaded.")
        return

    for idx, row in pairwise_df.iterrows():
        trial_id = row["trial_id"]
        expander_title = f"Comparison {idx + 1} of {len(pairwise_df)} — {trial_id}"

        with st.expander(expander_title, expanded=True):
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("### Clip A")
                render_audio_player(row["audio_A_path"])

            with col_b:
                st.markdown("### Clip B")
                render_audio_player(row["audio_B_path"])

            st.radio(
                        "Which clip has better Musicality?",
                        options=["A", "B"],
                        index=None,
                        key=f"pairwise_{trial_id}_better_overall",
                        horizontal=True,
                    )

            st.radio(
                        "Which clip sounds more authentically Carnatic?",
                        options=["A", "B"],
                        index=None,
                        key=f"pairwise_{trial_id}_more_carnatic",
                        horizontal=True,
                    )

            st.radio(
                        "Which clip has smoother continuation?",
                        options=["A", "B"],
                        index=None,
                        key=f"pairwise_{trial_id}_smoother",
                        horizontal=True,
                    )

            st.text_area(
                            "Other Feedback (if any):",
                            key=f"pairwise_{trial_id}_comment",
                            placeholder="Any other feedback on the Clip comparison",
                        )

    if st.button("Submit Pairwise Section", type="primary"):
        trial_ids = pairwise_df["trial_id"].tolist()
        is_valid, msg = validate_pairwise_section(trial_ids)

        if not is_valid:
            st.error(msg)
            return

        if not st.session_state.pairwise_saved:
            rows = build_pairwise_response_rows(
                                                    st.session_state.participant_id,
                                                    pairwise_df,
                                                )
            if USE_GOOGLE_SHEETS:
                save_pairwise_responses_gsheet(rows, GOOGLE_SPREADSHEET_ID)
            else:
                save_pairwise_responses(rows, PAIRWISE_RESPONSES_CSV)        
        
            # save_pairwise_responses(rows, PAIRWISE_RESPONSES_CSV)
            # save_pairwise_responses_gsheet(rows, GOOGLE_SHEET_NAME)
            st.session_state.pairwise_saved = True

        st.session_state.stage = "final"
        st.rerun()


def show_final_page():
    st.title("Thank You")
    render_instructions_expander("final")

    st.info(f"You can now close this window.")

def main():
    st.set_page_config(
                        page_title="Master's Capstone Survey",
                        layout="wide",
                    )
    init_session_state()

    if st.session_state.stage == "welcome":
        show_welcome_page()
    elif st.session_state.stage == "profile":
        show_profile_page()
    elif st.session_state.stage == "likert":
        show_likert_page()
    elif st.session_state.stage == "pairwise":
        show_pairwise_page()
    elif st.session_state.stage == "final":
        show_final_page()


if __name__ == "__main__":
    main()
