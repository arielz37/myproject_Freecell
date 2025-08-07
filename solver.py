import tkinter as tk
from tkinter import messagebox, scrolledtext
from HSD_3 import State, hsd_solver 

def solve():
    input_text = input_box.get("1.0", tk.END).strip()
    try:
        state = State.from_text_block(input_text)
    except Exception as e:
        messagebox.showerror("Parse Error", f"Failed to parse input deal:\n{e}")
        return

    try:
        result_state, path = hsd_solver(state, k=6, N=100000, timeout=300)
        if result_state:
            output = "\n".join(str(move) for move in path)
            output_box.delete("1.0", tk.END)
            output_box.insert(tk.END, output)
        else:
            output_box.delete("1.0", tk.END)
            output_box.insert(tk.END, "Failed to solve within time limit.")
    except Exception as e:
        messagebox.showerror("Solve Error", str(e))

# --- Build UI ---
root = tk.Tk()
root.title("FreeCell Solver")

# Input area
tk.Label(root, text="Please input the deal:").pack()
input_box = scrolledtext.ScrolledText(root, width=80, height=12)
input_box.pack()

# Solve button
tk.Button(root, text="Solve", command=solve).pack(pady=10)

# Output area
tk.Label(root, text="Solution:").pack()
output_box = scrolledtext.ScrolledText(root, width=80, height=12)
output_box.pack()

root.mainloop()
