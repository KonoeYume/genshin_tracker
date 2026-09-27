import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

DATABASE = Path(__file__).with_name("genshin_tracker.db")


@app.get("/requirements")
def get_requirements():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute("""
            SELECT
                characters.name AS character,
                materials.name AS material,
                ascension_costs.quantity AS required,
                COALESCE(inventory.quantity, 0) AS owned
            FROM ascension_costs
            JOIN characters
                ON characters.id = ascension_costs.character_id
            JOIN materials
                ON materials.id = ascension_costs.material_id
            LEFT JOIN inventory
                ON inventory.material_id = materials.id
            WHERE ascension_costs.from_ascension >= characters.current_ascension
              AND ascension_costs.from_ascension < characters.target_ascension
        """).fetchall()

        return [
            {
                "character": row["character"],
                "material": row["material"],
                "required": row["required"],
                "owned": row["owned"],
                "still_needed": max(row["required"] - row["owned"], 0),
            }
            for row in rows
        ]
    finally:
        connection.close()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html>
    <html>
      <head>
        <title>Genshin Tracker</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; }
          table { border-collapse: collapse; width: 100%; }
          th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
          th { background: #eee; }
        </style>
      </head>
      <body>
        <h1>Genshin Tracker</h1>
        <section>
          <h2>Character goal</h2>
          <label for="character-select">Character:</label>
          <select id="character-select" onchange="loadGoal()"></select>
          <p>Current ascension: <span id="current-ascension"></span></p>
          <label for="target-ascension">Target ascension:</label>
          <input id="target-ascension" type="number" min="0" max="6" step="1">
          <button onclick="saveGoal()">Save goal</button>
          <p id="goal-message"></p>
        </section>
        <h2>Materials needed</h2>
        <table>
          <thead>
            <tr>
              <th>Character</th><th>Material</th>
              <th>Required</th><th>Owned</th><th>Still needed</th>
            </tr>
          </thead>
          <tbody id="requirements"></tbody>
        </table>

        <script>
          async function loadRequirements() {
            const response = await fetch("/requirements");
            const items = await response.json();
            const table = document.getElementById("requirements");

            table.replaceChildren();

            for (const item of items) {
              const row = table.insertRow();

              row.insertCell().textContent = item.character;
              row.insertCell().textContent = item.material;
              row.insertCell().textContent = item.required;

              const ownedCell = row.insertCell();
              const input = document.createElement("input");
              input.type = "number";
              input.min = "0";
              input.step = "1";
              input.value = item.owned;
              input.style.width = "70px";
              ownedCell.append(input);

              const neededCell = row.insertCell();
              neededCell.textContent = item.still_needed;

              const button = document.createElement("button");
              button.textContent = "Save";
              ownedCell.append(" ", button);

              button.addEventListener("click", async () => {
                const quantity = Number(input.value);

                if (!Number.isInteger(quantity) || quantity < 0) {
                  alert("Enter a whole number of zero or more.");
                  return;
                }

                const saveResponse = await fetch("/inventory", {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    material_name: item.material,
                    quantity: quantity
                  })
                });

                if (!saveResponse.ok) {
                  alert("Could not save the inventory amount.");
                  return;
                }

                await loadRequirements();
              });
            }
          }
          async function loadGoal() {
              const name = document.getElementById("character-select").value;
              const response = await fetch(`/characters/${encodeURIComponent(name)}`);
              const character = await response.json();

              document.getElementById("current-ascension").textContent =
                character.current_ascension;

              const input = document.getElementById("target-ascension");
              input.value = character.target_ascension;
              input.min = character.current_ascension;
            }

            async function saveGoal() {
              const input = document.getElementById("target-ascension");
              const target = Number(input.value);
              const message = document.getElementById("goal-message");
              const name = document.getElementById("character-select").value;

              if (!Number.isInteger(target) || target < Number(input.min) || target > 6) {
                message.textContent = "Enter a valid target ascension.";
                return;
              }

              const response = await fetch(`/characters/${encodeURIComponent(name)}/goal`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target_ascension: target })
              });

              if (!response.ok) {
                message.textContent = "Could not save the goal.";
                return;
              }

              message.textContent = "Goal saved.";
              await loadRequirements();
            }
            async function loadCharacters() {
              const response = await fetch("/characters");
              const characters = await response.json();
              const select = document.getElementById("character-select");

              select.replaceChildren();

              for (const character of characters) {
                const option = document.createElement("option");
                option.value = character.name;
                option.textContent = character.name;
                select.append(option);
              }

              if (characters.length > 0) {
                await loadGoal();
              }
            }
          loadCharacters();
          loadRequirements();
        </script>
      </body>
    </html>
    """

class InventoryUpdate(BaseModel):
    material_name: str
    quantity: int = Field(ge=0)


@app.put("/inventory")
def update_inventory(update: InventoryUpdate):
    connection = sqlite3.connect(DATABASE)

    try:
        material = connection.execute(
            "SELECT id FROM materials WHERE name = ?",
            (update.material_name,)
        ).fetchone()

        if material is None:
            raise HTTPException(status_code=404, detail="Material not found")

        connection.execute("""
            INSERT INTO inventory (material_id, quantity)
            VALUES (?, ?)
            ON CONFLICT(material_id)
            DO UPDATE SET quantity = excluded.quantity
        """, (material[0], update.quantity))

        connection.commit()

        return {
            "material": update.material_name,
            "owned": update.quantity
        }
    finally:
        connection.close()

class GoalUpdate(BaseModel):
    target_ascension: int = Field(ge=0, le=6)


@app.put("/characters/{character_name}/goal")
def update_character_goal(character_name: str, goal: GoalUpdate):
    connection = sqlite3.connect(DATABASE)

    try:
        character = connection.execute("""
            SELECT current_ascension
            FROM characters
            WHERE name = ?
        """, (character_name,)).fetchone()

        if character is None:
            raise HTTPException(status_code=404, detail="Character not found")

        if goal.target_ascension < character[0]:
            raise HTTPException(
                status_code=400,
                detail="Target cannot be below current ascension"
            )

        connection.execute("""
            UPDATE characters
            SET target_ascension = ?
            WHERE name = ?
        """, (goal.target_ascension, character_name))

        connection.commit()
        return {
            "character": character_name,
            "target_ascension": goal.target_ascension
        }
    finally:
        connection.close()

@app.get("/characters/{character_name}")
def get_character(character_name: str):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        row = connection.execute("""
            SELECT name, current_ascension, target_ascension
            FROM characters
            WHERE name = ?
        """, (character_name,)).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Character not found")

        return dict(row)
    finally:
        connection.close()

@app.get("/characters")
def list_characters():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute("""
            SELECT name, current_ascension, target_ascension
            FROM characters
            ORDER BY name
        """).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()