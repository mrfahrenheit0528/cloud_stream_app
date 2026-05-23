import flet as ft
with open("icons_out.txt", "w") as f:
    for name in dir(ft.icons):
        if "REPEAT" in name.upper() or "LOOP" in name.upper() or "ONE" in name.upper():
            f.write(name + "\n")
