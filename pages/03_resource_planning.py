"""
Resource Planning Module for AWS Migration Strategy.

This page provides functionality to develop resource planning based on
migration strategy, wave planning data, and resource details.
"""

import re

import streamlit as st

from prompt_library.resource_planning.resource_planning_prompt import (
    get_resource_planning_prompt,
)
from utils.bedrock_client import invoke_bedrock_model_with_reasoning
from utils.file_handler import read_csv_file


def page_details():
    """Display the main page details and description for resource planning."""
    st.title("Develop Resource Plan for the Migration Strategy")
    aws_resource_planning = """
        Develop resource planning based on three key inputs:
        * (1) migration strategy,
        * (2) wave planning data, and
        * (3) resource details.

        It creates detailed team structures and resource allocation plans,
        providing five key outputs: an executive summary, team structure
        evaluation, resource summary, wave-based planning, and role-based
        resource allocation. The focus is on two team structure models
        (Hub-and-Spoke and Wave-Based), with justification for the
        recommended approach.
        """
    st.markdown(aws_resource_planning)
    st.header("Upload migration strategy document with wave planning")


def develop_resource_planning(strategy_content):
    """
    Develop resource planning based on migration strategy content.

    Args:
        strategy_content (str): The migration strategy document content.
    """
    pattern = r"\|(.*?)\|[\r\n]"
    wave_planning_data = re.findall(pattern, strategy_content)
    if not wave_planning_data:
        wave_planning_data = ""

    resource_details = read_csv_file("resource_profile")
    with st.expander("Resource Profile"):
        st.dataframe(resource_details)

    resource_prompt = get_resource_planning_prompt(
        strategy_content, wave_planning_data, resource_details
    )
    resource_planning_data = invoke_bedrock_model_with_reasoning(resource_prompt)

    if resource_planning_data and resource_planning_data.get("success", False):
        st.markdown(resource_planning_data["response"])
        print("*" * 80)
        print(resource_planning_data["reasoning"])
        st.download_button(
            label="Download Strategy",
            data=resource_planning_data["response"],
            file_name="aws_resource_planning_data.md",
            mime="text/markdown",
        )
    elif resource_planning_data:
        st.error(
            f"Error generating resource planning: "
            f"{resource_planning_data.get('error', 'Unknown error')}"
        )
    else:
        st.error("Failed to generate resource planning data")


if __name__ == "__main__":
    page_details()
    migration_strategy = st.file_uploader(
        "Upload migration strategy document with wave plan"
    )
    if st.button("Generate Resource Planning", type="primary"):
        if migration_strategy:
            with st.spinner(
                "The resource planning is being developed. This may take a few minutes."
            ):
                develop_resource_planning(migration_strategy.read().decode("utf-8"))
