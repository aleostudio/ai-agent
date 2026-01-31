from langchain_core.prompts import PromptTemplate

# ------------------------------------------------------------
# Here you can create every prompt you will use in your agent.
# Every prompt could have defided placeholders.
# Use these prompts in your code in this way:
# ------------------------------------------------------------
#
# import app.prompts as prompts
# ...
#
# prompt = prompts.YOUR_CUSTOM_PROMPT.format(
#     style = state.get("style", settings.DEFAULT_STYLE),
#     focus = state.get("focus", settings.DEFAULT_FOCUS),
# )
#
# response = self.model.invoke(prompt)

YOUR_CUSTOM_PROMPT = PromptTemplate(
    input_variables = ["style", "focus"],
    template = """
    ### ROLE: THE ROLE YOU WANT TO ASSIGN TO THE LLM ###

    Write here what LLM has to do.

    📌 **Guidelines:**
    - Write here first guideline (eg. Mantain the same setting, mood and tone established by the user).
    - You can add more guidelines.

    **Narrative style:** {style}
    **Focus:** {focus}

    Provide only the response text, without double quotes.

    🎭 **Response:**
    """
)
