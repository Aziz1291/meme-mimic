"""The coach's 5 tools: a Python function + a JSON Schema for each.

The model can only ASK for a tool; executor.py decides. No tool takes a session id:
the server gives each tool the current player's game, so the coach can't read other games.
No tool deletes or changes anything: the only "action" is a PROPOSAL the player confirms.
"""

# Fixed advice written by us. The model rephrases it; it doesn't invent coaching.
TIPS = {
    "timbre": "Copy the voice's color: same mouth shape, same nasal or breathy sound. "
              "Exaggerate it a little, memes are cartoons.",
    "melody": "Hum the original first without words, following where it goes up and down. "
              "Then add the words on that melody.",
    "loudness": "Copy where it gets loud and quiet: punch the loud words, soften the rest. "
                "Stay at the same distance from the mic.",
    "rhythm": "Tap the beat of the original while you listen, then say it at the same speed. "
              "Don't rush the start.",
}


# --- The tools (each one reads the game the SERVER gives it) ---

def best_try(section: dict) -> dict | None:
    if not section["tries"]:
        return None
    return max(section["tries"], key=lambda attempt: attempt["percent"])


def get_session_summary(game: dict) -> dict:
    played = [section for section in game["sections"] if section["tries"]]
    if not played:
        return {"error": "no scored attempt yet"}
    best_percents = [best_try(section)["percent"] for section in played]
    best = max(played, key=lambda section: best_try(section)["percent"])
    worst = min(played, key=lambda section: best_try(section)["percent"])
    return {"meme": game["meme_title"], "section_count": len(game["sections"]),
            "total_percent": round(sum(best_percents) / len(best_percents)),
            "best": {"section_number": best["section_number"], "percent": best_try(best)["percent"]},
            "worst": {"section_number": worst["section_number"], "percent": best_try(worst)["percent"]}}


def get_section_scores(game: dict, section_number: int) -> dict:
    section = game["sections"][section_number - 1]
    if not section["tries"]:
        return {"error": "this section has no scored attempt yet"}
    latest = section["tries"][-1]
    return {"section_number": section_number, "subtitle": section["subtitle"],
            "percent": latest["percent"], "verdict": latest["verdict"],
            "sub_scores_percent": latest["sub_scores_percent"], "tries": len(section["tries"])}


def compare_attempts(game: dict, section_number: int) -> dict:
    section = game["sections"][section_number - 1]
    if not section["tries"]:
        return {"error": "this section has no scored attempt yet"}
    first = section["tries"][0]["percent"]
    latest = section["tries"][-1]["percent"]
    return {"section_number": section_number, "tries": len(section["tries"]),
            "first_percent": first, "latest_percent": latest, "change_points": latest - first}


def get_tip(game: dict, weak_point: str) -> dict:
    return {"weak_point": weak_point, "tip": TIPS[weak_point]}


def propose_retry(game: dict, section_number: int) -> dict:
    # Only a proposal: the loop turns it into a pending action, the player clicks to confirm.
    return {"proposed": True, "section_number": section_number,
            "note": "The player must confirm in the app."}


# --- The JSON Schemas the model sees. The description IS the instruction. ---

def section_parameter(section_count: int) -> dict:
    return {"type": "object",
            "properties": {"section_number": {
                "type": "integer", "minimum": 1, "maximum": section_count,
                "description": "The piece number as the player says it: 1 is the first piece."}},
            "required": ["section_number"], "additionalProperties": False}


def tool_schemas(section_count: int) -> list[dict]:
    no_parameters = {"type": "object", "properties": {}, "required": [],
                     "additionalProperties": False}
    tools = [
        ("get_session_summary", "Gets the player's total score and their best and worst pieces. "
         "Use for questions about the whole game.", no_parameters),
        ("get_section_scores", "Gets the latest score of one piece and its 4 sub-scores "
         "(timbre, melody, loudness, rhythm) in %.", section_parameter(section_count)),
        ("compare_attempts", "Compares the player's first and latest try on one piece. "
         "Use when the player asks if they improved.", section_parameter(section_count)),
        ("get_tip", "Gets a fixed tip to improve one weak point. Use when the player asks for "
         "advice.", {"type": "object",
                     "properties": {"weak_point": {"type": "string",
                                                   "enum": list(TIPS.keys())}},
                     "required": ["weak_point"], "additionalProperties": False}),
        ("propose_retry", "Proposes that the player retries one piece. Use ONLY when the player "
         "explicitly asks to redo or retry a specific piece. Do not use it when the player only "
         "complains or comments. The player must still confirm in the app.",
         section_parameter(section_count)),
    ]
    schemas = []
    for name, description, parameters in tools:
        schemas.append({"type": "function", "function": {
            "name": name, "description": description, "parameters": parameters}})
    return schemas
