import sqlite3

connection = sqlite3.connect("genshin_tracker.db")
connection.row_factory = sqlite3.Row

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

for row in rows:
    still_needed = max(row["required"] - row["owned"], 0)
    print(
        f'{row["character"]}: {row["material"]} — '
        f'{row["required"]} required, {row["owned"]} owned, '
        f'{still_needed} still needed'
    )

connection.close()