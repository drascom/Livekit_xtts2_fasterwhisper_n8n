from livekit.agents import function_tool, RunContext
import webbrowser

@function_tool
async def open_url(url: str, context: RunContext)-> str:
    """
    Opens a URL in the user's default web browser.
    """
    try:
        webbrowser.open(url)
        return f"Opened {url} in your web browser."
    except Exception as e:
        return f"Failed to open {url}. Error: {str(e)}"