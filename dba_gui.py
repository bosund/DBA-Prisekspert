"""
DISCLAIMER:
Dette program er udelukkende udviklet til uddannelsesmæssige (educational) formål 
og som et personligt projekt. Det er op til brugeren af programmet at overholde gældende 
lovgivning samt handelsbetingelser (Terms of Service) for de hjemmesider, der interageres med. 
Forfatteren tager intet ansvar for misbrug eller blokeringer forårsaget af dette værktøj.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import sys
import os

import scrape_all

class DBAScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DBA Scraper")
        self.root.geometry("600x500")
        
        # Frame for inputs
        input_frame = ttk.LabelFrame(root, text="Indstillinger", padding=(10, 10))
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        # Søgestreng
        ttk.Label(input_frame, text="Søgestreng (Fritekst):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.query_var = tk.StringVar(value="fender stratocaster")
        ttk.Entry(input_frame, textvariable=self.query_var, width=50).grid(row=0, column=1, sticky=tk.W, pady=2)

        # URL
        ttk.Label(input_frame, text="ELLER direkte URL:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.url_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.url_var, width=50).grid(row=1, column=1, sticky=tk.W, pady=2)

        # Sider
        ttk.Label(input_frame, text="Maks antal sider:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pages_var = tk.IntVar(value=5)
        ttk.Spinbox(input_frame, from_=1, to=1000, textvariable=self.pages_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)

        # Output fil
        ttk.Label(input_frame, text="Output filnavn:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.output_var = tk.StringVar(value="dba_oversigt.md")
        ttk.Entry(input_frame, textvariable=self.output_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=2)

        # Start Button
        self.start_btn = ttk.Button(root, text="Start Scraping", command=self.start_scraping)
        self.start_btn.pack(pady=5)

        # Output Text
        ttk.Label(root, text="Log:").pack(anchor=tk.W, padx=10)
        self.log_text = scrolledtext.ScrolledText(root, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_scraping(self):
        query = self.query_var.get().strip()
        url = self.url_var.get().strip()
        pages = self.pages_var.get()
        output = self.output_var.get().strip()

        if not query and not url:
            messagebox.showwarning("Fejl", "Du skal angive enten en søgestreng eller en URL.")
            return

        self.start_btn.config(state=tk.DISABLED)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Run in a background thread to prevent GUI freezing
        thread = threading.Thread(target=self.run_script, args=(query, url, pages, output))
        thread.daemon = True
        thread.start()

    def run_script(self, query, url, pages, output):
        def gui_logger(msg):
            self.root.after(0, self.log, msg)

        try:
            results = scrape_all.get_all_ads(query, url, pages, log_func=gui_logger)
            if not results:
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                return

            categories = list(set(r['category_path'] for r in results))
            categories.sort()

            # Trigger the filter popup on the main thread
            self.root.after(0, self.show_category_filter, results, categories, output, query, url, pages)
            
        except Exception as e:
            gui_logger(f"\n--- EXCEPTION: {str(e)} ---")
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

    def show_category_filter(self, results, categories, output, query, url, pages):
        popup = tk.Toplevel(self.root)
        popup.title("Vælg Kategorier")
        popup.geometry("500x400")
        popup.transient(self.root)
        popup.grab_set()

        ttk.Label(popup, text="Vælg hvilke kategorier du vil inkludere i oversigten:").pack(pady=10, padx=10, anchor=tk.W)

        frame = ttk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Scrolled frame logic for categories (using Canvas)
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checkbox_vars = {}
        for cat in categories:
            var = tk.BooleanVar(value=True)
            checkbox_vars[cat] = var
            cb = ttk.Checkbutton(scrollable_frame, text=cat, variable=var)
            cb.pack(anchor=tk.W, pady=2)

        def on_ok():
            selected_cats = {cat for cat, var in checkbox_vars.items() if var.get()}
            filtered_results = [r for r in results if r['category_path'] in selected_cats]
            
            title = url if url else query.title()
            
            output_path = output
            if not os.path.isabs(output_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                output_path = os.path.join(script_dir, output_path)

            try:
                scrape_all.write_markdown(filtered_results, output_path, title, pages)
                self.log(f"\n--- SUCCES: Scraping færdig. Gemt {len(filtered_results)} annoncer i {output} ---")
            except Exception as e:
                self.log(f"\n--- FEJL under gem: {str(e)} ---")
                
            self.start_btn.config(state=tk.NORMAL)
            popup.destroy()

        ttk.Button(popup, text="OK", command=on_ok).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = DBAScraperGUI(root)
    root.mainloop()
