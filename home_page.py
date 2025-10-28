"""
This page provides information about core features of the demo.
"""

import streamlit as st

for key in st.session_state.keys():
    del st.session_state[key]

# Title and Introduction
st.title("Gen AI: Art of Possibility for AWS MAP Use Cases")
# Content on the right side
st.markdown("""
    This demo illustrates the application of Generative AI during the MAP assessment phase, following the completion of on-premises discovery. It showcases capabilities that enhance migration planning, cost optimisation, identification of modernisation opportunities, and resource planning, processes which were previously both time-consuming and complex.
    - This demo can analyse infrastructure data to generate strategic recommendations, predict MAP funding milestones, and create migration wave plans.
    """)
    
st.header("Key features:")
st.markdown("""
- **Modernisation Opportunity Analysis**: GenAI analyses architecture and on-premises infrastructure data to identify modernisation pathways with corresponding AWS cost projections.
- **Migration Strategy Development**: Creates data-driven migration patterns, wave planning with cumulative spend forecasts, and $50k milestone predictions to accelerate migration.
- **Resource Planning**: Resource planning is based on three key inputs: migration strategy, wave planning data, and resource details. It creates detailed team structures and resource allocation plans, providing five key outputs: an executive summary, team structure evaluation, resource summary, wave-based planning, and role-based resource allocation. The focus is on two team structure models (Hub-and-Spoke and Wave-Based), with justification for the recommended approach.

""")

st.warning(
    """ **AI Accuracy Disclaimer**: While our GenAI provides valuable insights, it might occasionally generate inaccurate predictions. Always validate and double-check AI-generated recommendations before implementation."""
)
st.warning(
    """**This solution is explicitly designed for proof-of-concept purposes** only to explore the art of possibility with Generative AI for MAP assessments. Please adhere to your company's enhanced security and compliance policies"""
)
