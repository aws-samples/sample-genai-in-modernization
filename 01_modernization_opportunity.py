"""
This page provides functionality to analyse IT inventory data and architecture
images to generate AWS modernisation recommendations.
"""

import pandas as pd
import streamlit as st

from prompt_library.modernization_opportunity.inventory_analysis_prompt import (
    get_inventory_analysis_prompt,
)
from prompt_library.modernization_opportunity.modernization_pathways_prompt import (
    get_modernization_pathways_prompt,
)
from prompt_library.modernization_opportunity.onprem_architecture_prompt import (
    get_onprem_architecture_prompt,
)
from utils.bedrock_client import (
    invoke_bedrock_model_for_image_analysis,
    invoke_bedrock_model_with_reasoning,
)
from utils.image_processor import convert_image_to_base64, get_image_type, resize_image

if "inventory_analysis" not in st.session_state:
    st.session_state["inventory_analysis"] = "inventory_analysis"
if "modz_analysis" not in st.session_state:
    st.session_state["modz_analysis"] = "modz_analysis"
if "onprem_architecture" not in st.session_state:
    st.session_state["onprem_architecture"] = "onprem_architecture"


def page_details():
    """Display page title and description."""
    st.title("Identify modernisation opportunity using on-premises discovery data")
    st.markdown("""
    You can identify AWS modernisation opportunities based on your IT inventory.
    Upload your IT inventory as a CSV file, define the scope of modernisation,
    and optionally provide an on-premises architecture image.
    """)


def generate_inventory_analysis(inventory_data_csv):
    """
    Generate inventory analysis from CSV data.

    Args:
        inventory_data_csv: CSV data as string containing inventory data

    Returns:
        Analysis response or None if error occurs
    """
    try:
        prompt = get_inventory_analysis_prompt(inventory_data_csv)
        analysis_result = invoke_bedrock_model_with_reasoning(prompt)

        if not analysis_result.get("success", False):
            error_msg = analysis_result.get("error", "Unknown error")
            st.error(f"Error generating inventory analysis: {error_msg}")
            return None

        print("*" * 80)
        print(analysis_result["reasoning"])
        return analysis_result["response"]
    except (ValueError, KeyError) as error:
        st.error(f"Error generating inventory analysis: {str(error)}")
        return None


def generate_architecture_analysis(architecture_file):
    """
    Generate architecture analysis from uploaded file.

    Args:
        architecture_file: Uploaded architecture image file

    Returns:
        Architecture description or None if error occurs
    """
    try:
        onprem_image = architecture_file.getvalue()
        # Resize image to prevent errors with large images
        resized_image = resize_image(onprem_image)
        encoded_image = convert_image_to_base64(resized_image)
        image_type = get_image_type(architecture_file.name)
        prompt = get_onprem_architecture_prompt()
        architecture_analysis = invoke_bedrock_model_for_image_analysis(
            encoded_image, prompt, image_type
        )
        return architecture_analysis
    except (ValueError, AttributeError) as error:
        st.error(f"Error generating architecture analysis: {str(error)}")
        return None


def recommend_modernisation_pathways(
    inventory_data_csv, modernisation_scope, architecture_description=None
):
    """
    Recommend modernisation pathways based on inventory and scope.

    Args:
        inventory_data_csv: CSV data as string containing inventory data
        modernisation_scope: Text describing modernisation scope
        architecture_description: Optional architecture description

    Returns:
        Modernisation recommendations or None if error occurs
    """
    try:
        prompt = get_modernization_pathways_prompt(
            inventory_data_csv, architecture_description, modernisation_scope
        )
        modernization_pathways = invoke_bedrock_model_with_reasoning(prompt)

        if not modernization_pathways.get("success", False):
            error_msg = modernization_pathways.get("error", "Unknown error")
            st.error(f"Error generating modernisation recommendations: {error_msg}")
            return None

        print("*" * 80)
        print(modernization_pathways["reasoning"])
        return modernization_pathways["response"]
    except (ValueError, KeyError) as error:
        st.error(f"Error parsing modernisation recommendations: {str(error)}")
        return None


if __name__ == "__main__":
    page_details()

    # File uploads
    col1, col2 = st.columns(2)
    with col1:
        inventory_file = st.file_uploader("📤 Upload IT Inventory (CSV)", type=["csv"])
    with col2:
        on_prem_arch_file = st.file_uploader(
            " 📤 Upload On premises architecture (optional)",
            type=["jpg", "jpeg", "png"],
        )
    # Scope text area
    scope_text = st.text_area(
        "Provide scope details", placeholder="Migration and Modernization", height=150
    )
    st.divider()
    if st.button("Analyze Inventory", type="primary"):
        if inventory_file is None:
            st.error("Please upload an IT inventory CSV file.")
        elif not scope_text:
            st.error("Please provide modernisation scope.")
        else:
            arch_description = None
            with st.expander("Inventory Data"):
                inventory_df = pd.read_csv(inventory_file)
                st.subheader("IT Inventory")
                st.dataframe(inventory_df)
            if on_prem_arch_file:
                with st.expander("On-prem Architecture"):
                    st.subheader("Architecture")
                    st.image(on_prem_arch_file)
            with st.spinner("Analyzing inventory data..."):
                # Read inventory file
                inventory_analysis = generate_inventory_analysis(inventory_df)
                st.session_state["inventory_analysis"] = inventory_analysis
            # Process target architecture if provided
            if on_prem_arch_file:
                with st.spinner(
                    "Inventory analysis competed. Now analyzing target architecture..."
                ):
                    arch_description = generate_architecture_analysis(on_prem_arch_file)
                    if arch_description:
                        st.session_state["onprem_architecture"] = arch_description

    if st.session_state["inventory_analysis"] != "inventory_analysis":
        st.subheader("Inventory Analysis ")
        with st.expander("Inventory analysis"):
            st.write(st.session_state["inventory_analysis"])
            st.download_button(
                label="Download output",
                data=st.session_state["inventory_analysis"],
                file_name="inventory_analysis.md",
                mime="text/markdown",
            )
    if st.session_state["onprem_architecture"] != "onprem_architecture":
        st.subheader("Architecture Analysis ")
        with st.expander("Architecture analysis"):
            st.write(st.session_state["onprem_architecture"])
            st.download_button(
                label="Download output",
                data=st.session_state["onprem_architecture"],
                file_name="onprem_architecture.md",
                mime="text/markdown",
            )

    modz_recommendations = ""
    if st.button("Provide modernisation recommendations", type="primary"):
        if inventory_file is None:
            st.error("Please upload an IT inventory CSV file.")
        elif not scope_text:
            st.error("Please provide modernisation scope.")
        else:
            with st.spinner("Generating modernisation recommendations..."):
                inventory_df = pd.read_csv(inventory_file)
                arch_description = st.session_state["onprem_architecture"]
                modz_recommendations = recommend_modernisation_pathways(
                    inventory_df, scope_text, arch_description
                )
                st.session_state["modz_analysis"] = modz_recommendations

    if st.session_state["modz_analysis"] != "modz_analysis":
        st.subheader("Modernisation Strategy")
        with st.expander("Modernisation Strategy"):
            st.write(st.session_state["modz_analysis"])
            st.download_button(
                label="Download output",
                data=st.session_state["modz_analysis"],
                file_name="aws_modernisation_strategy.md",
                mime="text/markdown",
            )
