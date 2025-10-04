import tkinter as tk
from multiprocessing import freeze_support
from app.gui.main_window import DashboardApp
import app.gui.callbacks as callbacks

if __name__ == "__main__":
    freeze_support()
    root = tk.Tk()
    app = DashboardApp(root)
    callbacks.initialize_analyzer(app)
    root.mainloop()