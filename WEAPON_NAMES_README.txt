Weapon selector labels
======================

Replace app_v2.py in your project folder and refresh the browser page.
The selector label is now Weapon. Each weapon's first copy is displayed
by weapon name only. Additional copies show the weapon name followed by
their optional label; if blank, they show Copy 2, Copy 3, and so on.

The numbers previously shown were database IDs across all weapons, not
per-weapon copy counts. IDs remain internal to preserve saved goals.
No database migration or inventory change is needed.
