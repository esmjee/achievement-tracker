import tkinter as tk
from tkinter import colorchooser, ttk
from typing import Callable, Optional


class AppearanceDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        background_color: str,
        opacity: float,
        on_change: Callable[[str, float], None],
    ) -> None:
        super().__init__(master)
        self.title("Appearance")
        self.resizable(False, False)
        self.on_change: Callable[[str, float], None] = on_change
        self.color: str = background_color

        padding_options: dict[str, int] = {"padx": 10, "pady": 6}
        body: ttk.Frame = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Background color:").grid(row=0, column=0, sticky="w", **padding_options)
        self.swatch: tk.Label = tk.Label(
            body, text="      ", bg=self.color, relief="solid", borderwidth=1, cursor="hand2",
        )
        self.swatch.grid(row=0, column=1, sticky="w", **padding_options)
        self.swatch.bind("<Button-1>", self.choose_color)

        ttk.Label(body, text="Opacity:").grid(row=1, column=0, sticky="w", **padding_options)
        self.opacity_variable: tk.DoubleVar = tk.DoubleVar(value=opacity)
        opacity_scale = ttk.Scale(
            body, from_=0.2, to=1.0, orient="horizontal", variable=self.opacity_variable, length=160,
            command=self.on_opacity_change,
        )
        opacity_scale.grid(row=1, column=1, sticky="ew", **padding_options)

        ttk.Button(body, text="Close", command=self.destroy).grid(row=2, column=0, columnspan=2, pady=(8, 0))

        self.grab_set()

    def choose_color(self, event: Optional[tk.Event] = None) -> None:
        chosen_color = colorchooser.askcolor(color=self.color, parent=self, title="Background color")
        if chosen_color and chosen_color[1]:
            self.color = chosen_color[1]
            self.swatch.config(bg=self.color)
            self.on_change(self.color, round(self.opacity_variable.get(), 2))

    def on_opacity_change(self, value: str) -> None:
        self.on_change(self.color, round(float(value), 2))
